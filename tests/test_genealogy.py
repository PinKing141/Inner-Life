"""Phase 5 — genealogy: birth, eligible heirs, continue-as-heir, inheritance.

The vertical slice: a player can have a child via the consider_child event,
that child ages alongside them, and on death the player can continue as
the child — preserving the lineage_id while resetting per-life systems
and applying an estate share.
"""
from __future__ import annotations

import pytest

from controller.game_controller import GameController
from core import events as event_engine, genealogy, sim
from core.content.events import EVENTS
from core.predicates import ChildCountAtMost, HasLivingChild
from core.rng import Rng
from core.state import GameState, Relationship


def _new(seed: int = 1) -> GameState:
    return sim.new_game(seed=seed, name="", gender="Female", country="US", talent="Sports")


def _give_partner(state: GameState, npc_id: int = 999, age: int = 28) -> None:
    """Drop a Partner relationship + matching Agent into the state so birth
    has the prerequisite it expects. Bypasses partner formation RNG so the
    tests don't depend on tick_partner happening to fire."""
    from core.agents import Agent
    state.relationships.append(Relationship(
        npc_id=npc_id, name="Alex Partner", kind="Partner",
        relationship=80, alive=True,
    ))
    state.agents.append(Agent(
        npc_id=npc_id, first_name="Alex", last_name="Partner",
        gender="NonBinary", role="Partner", age=age,
        country=state.character.country if state.character else "US",
        city=state.character.city if state.character else "",
    ))


# --- Birth ---------------------------------------------------------------


def test_have_child_mints_an_agent_and_records_npc_id():
    s = _new()
    _give_partner(s)
    note = genealogy.have_child(s, Rng(1).fork(7))
    assert note is not None
    assert s.character.children, "child npc_id should be recorded on Character"
    child_id = s.character.children[-1]
    child_agent = next(a for a in s.agents if a.npc_id == child_id)
    assert child_agent.role == "Child"
    assert child_agent.age == 0
    assert child_agent.alive is True


def test_have_child_creates_player_facing_relationship():
    s = _new()
    _give_partner(s)
    genealogy.have_child(s, Rng(2).fork(7))
    child_id = s.character.children[-1]
    rel = next((r for r in s.relationships if r.npc_id == child_id), None)
    assert rel is not None
    assert rel.kind == "Child"
    assert rel.alive is True


def test_have_child_no_ops_without_partner():
    s = _new()
    note = genealogy.have_child(s, Rng(3).fork(7))
    assert note is None
    assert s.character.children == []


def test_child_stats_biased_by_parents_with_jitter():
    """The child's smarts/looks are biased toward the average of the
    player's stat and a midpoint of 60 — high-stat parents tend to
    produce high-stat children, but never deterministically."""
    s = _new()
    _give_partner(s)
    s.stats.smarts = 100
    s.stats.looks = 100
    genealogy.have_child(s, Rng(5).fork(7))
    child = next(a for a in s.agents if a.role == "Child")
    # mean of (100, 60) is 80; with ±10 jitter the child should land >= 60.
    assert child.smarts >= 60
    assert child.looks >= 60


# --- Predicates ----------------------------------------------------------


def test_has_living_child_predicate_flips_on_birth():
    s = _new()
    _give_partner(s)
    assert HasLivingChild()(s) is False
    genealogy.have_child(s, Rng(8).fork(7))
    assert HasLivingChild()(s) is True


def test_child_count_at_most_caps_the_birth_event():
    s = _new()
    s.character.children = [101, 102]
    assert ChildCountAtMost(2)(s) is True
    s.character.children.append(103)
    assert ChildCountAtMost(2)(s) is False


# --- Event end-to-end ----------------------------------------------------


def test_consider_child_event_routes_through_genealogy_side_effect():
    """Choosing 'Yes — start a family' on the catalogue event must mint
    a child through the same code path as the direct call."""
    s = _new()
    _give_partner(s)
    ev = event_engine.get_event("consider_child")
    assert ev is not None
    s.pending_event_id = ev["id"]
    event_engine.resolve_choice(s, ev["id"], 0)
    assert s.character.children, "side_effect should have minted a child"


def test_consider_child_decline_does_not_mint():
    s = _new()
    _give_partner(s)
    ev = event_engine.get_event("consider_child")
    assert ev is not None
    s.pending_event_id = ev["id"]
    event_engine.resolve_choice(s, ev["id"], 1)
    assert s.character.children == []


# --- Eligible heirs ------------------------------------------------------


def test_eligible_heirs_lists_only_living_children_in_id_order():
    s = _new()
    _give_partner(s)
    genealogy.have_child(s, Rng(11).fork(7))
    genealogy.have_child(s, Rng(13).fork(7))
    # Kill the first child to verify the filter.
    first_id = s.character.children[0]
    first_agent = next(a for a in s.agents if a.npc_id == first_id)
    first_agent.alive = False
    heirs = genealogy.eligible_heirs(s)
    assert [h["npc_id"] for h in heirs] == [s.character.children[1]]


def test_eligible_heirs_empty_without_living_descendants():
    s = _new()
    assert genealogy.eligible_heirs(s) == []


# --- Estate distribution -------------------------------------------------


def test_estate_share_taxed_and_split_evenly():
    s = _new()
    _give_partner(s)
    genealogy.have_child(s, Rng(21).fork(7))
    genealogy.have_child(s, Rng(22).fork(7))
    s.money = 100_000
    heir_id = s.character.children[0]
    share = genealogy.estate_share_for(s, heir_id)
    # 100k * (1 - 0.40) / 2 heirs = 30_000
    assert share == 30_000


def test_estate_share_is_zero_on_debt():
    s = _new()
    _give_partner(s)
    genealogy.have_child(s, Rng(31).fork(7))
    s.money = -50_000
    heir_id = s.character.children[0]
    assert genealogy.estate_share_for(s, heir_id) == 0


def test_estate_share_zero_for_unknown_heir():
    s = _new()
    _give_partner(s)
    genealogy.have_child(s, Rng(41).fork(7))
    s.money = 100_000
    assert genealogy.estate_share_for(s, 999999) == 0


# --- Continue as heir ----------------------------------------------------


def test_continue_as_heir_refuses_outside_death_mode():
    s = _new()
    _give_partner(s)
    genealogy.have_child(s, Rng(51).fork(7))
    heir_id = s.character.children[0]
    # Still PLAYING — must refuse.
    assert genealogy.continue_as_heir(s, heir_id) is False


def test_continue_as_heir_pivots_character_and_preserves_lineage():
    s = _new(seed=77)
    _give_partner(s)
    genealogy.have_child(s, Rng(61).fork(7))
    heir_id = s.character.children[0]
    heir_age = next(a.age for a in s.agents if a.npc_id == heir_id)
    parent_first = s.character.first_name
    lineage = s.character.lineage_id
    s.money = 80_000
    s.mode = "DEATH"

    ok = genealogy.continue_as_heir(s, heir_id)
    assert ok is True
    assert s.mode == "PLAYING"
    # Outgoing life archived.
    assert s.ancestors and s.ancestors[-1]["first_name"] == parent_first
    # New Character carries the heir's identity + the preserved lineage.
    assert s.character.first_name != parent_first
    assert s.character.age == heir_age
    assert s.character.lineage_id == lineage
    # Inheritance applied: 80k * 0.60 / 1 heir = 48_000.
    assert s.money == 48_000
    # The heir is gone from agents/relationships (they're the player now).
    assert all(a.npc_id != heir_id for a in s.agents)
    assert all(r.npc_id != heir_id for r in s.relationships)


def test_continue_as_heir_resets_per_life_subsystems():
    s = _new(seed=77)
    _give_partner(s)
    genealogy.have_child(s, Rng(81).fork(7))
    heir_id = s.character.children[0]
    # Dirty the per-life slots.
    s.fired_events = ["nursery_bully"]
    s.feed.append(s.feed[0])
    s.education.in_school = True
    s.education.level = "University"
    s.career = None
    s.exam = {"finished": False}
    s.mode = "DEATH"
    genealogy.continue_as_heir(s, heir_id)
    assert s.fired_events == []
    assert s.education.in_school is False
    assert s.education.level == "None"
    assert s.exam is None
    # Feed reset, but a generational marker entry exists.
    assert len(s.feed) == 1
    assert "inherited" in s.feed[0].text.lower()


def test_continue_as_heir_drops_old_partner_friends_and_grandparents():
    """The deceased's Partner / Friends / Mother / Father must NOT carry
    over as the heir's romantic partner / friends / parents. Otherwise the
    sim's `kind == 'Partner'` checks treat a step-parent as the heir's
    spouse and consider_child fires on the wrong person."""
    s = _new(seed=77)
    _give_partner(s, npc_id=900)
    # Seed a couple of arbitrary friends/coworkers on the deceased.
    from core.agents import Agent
    for npc_id, kind in ((500, "Friend"), (501, "Coworker")):
        s.agents.append(Agent(
            npc_id=npc_id, first_name="Pal", last_name="X",
            gender="NonBinary", role=kind, age=35,
            country=s.character.country, city=s.character.city,
        ))
        s.relationships.append(Relationship(
            npc_id=npc_id, name="Pal X", kind=kind, relationship=60, alive=True,
        ))
    genealogy.have_child(s, Rng(61).fork(7))
    heir_id = s.character.children[0]
    s.mode = "DEATH"

    genealogy.continue_as_heir(s, heir_id)

    kinds = {r.kind for r in s.relationships if r.alive}
    assert "Partner" not in kinds
    assert "Friend" not in kinds
    assert "Coworker" not in kinds
    # The original Mother/Father (heir's grandparents) drop too — they
    # belonged to the deceased's life, not the heir's.
    assert all(r.kind not in ("Mother", "Father") or r.npc_id == 900
               for r in s.relationships)


def test_surviving_partner_becomes_heirs_parent():
    """The deceased's living Partner is the heir's biological other
    parent, so they reclassify to Mother/Father based on gender."""
    s = _new(seed=77)
    _give_partner(s, npc_id=900)
    # Make the partner female so we land on Mother.
    partner_agent = next(a for a in s.agents if a.npc_id == 900)
    partner_agent.gender = "Female"
    genealogy.have_child(s, Rng(63).fork(7))
    heir_id = s.character.children[0]
    s.mode = "DEATH"

    genealogy.continue_as_heir(s, heir_id)
    mom = next((r for r in s.relationships if r.kind == "Mother"), None)
    assert mom is not None
    assert mom.npc_id == 900
    assert mom.alive is True
    # The Agent's role moved with the relationship — keep the two aligned.
    assert next(a for a in s.agents if a.npc_id == 900).role == "Mother"


def test_other_living_children_become_heirs_siblings():
    s = _new(seed=77)
    _give_partner(s)
    genealogy.have_child(s, Rng(71).fork(7))
    genealogy.have_child(s, Rng(72).fork(7))
    heir_id, sibling_id = s.character.children[0], s.character.children[1]
    s.mode = "DEATH"

    genealogy.continue_as_heir(s, heir_id)
    sib = next((r for r in s.relationships if r.npc_id == sibling_id), None)
    assert sib is not None
    assert sib.kind == "Sibling"
    assert sib.alive is True


def test_dead_partner_does_not_become_parent():
    """If the partner pre-deceased the player, they don't get resurrected
    as the heir's parent — they stay gone."""
    s = _new(seed=77)
    _give_partner(s, npc_id=900)
    # Have the child while the partner is still alive (birth requires it),
    # then kill the partner before the death-and-continue transition.
    genealogy.have_child(s, Rng(81).fork(7))
    heir_id = s.character.children[0]
    next(a for a in s.agents if a.npc_id == 900).alive = False
    next(r for r in s.relationships if r.npc_id == 900).alive = False
    s.mode = "DEATH"
    genealogy.continue_as_heir(s, heir_id)
    assert not any(r.kind in ("Mother", "Father") and r.npc_id == 900
                   for r in s.relationships)


def test_consider_child_event_is_not_unique():
    """Without `unique: False`, the event is marked fired after the first
    resolution and ChildCountAtMost(2) can never offer a sibling."""
    s = _new()
    _give_partner(s)
    ev = event_engine.get_event("consider_child")
    assert ev is not None
    s.pending_event_id = ev["id"]
    event_engine.resolve_choice(s, ev["id"], 0)  # have first child
    assert "consider_child" not in s.fired_events, (
        "non-unique event should not be recorded in fired_events"
    )


def test_continue_as_heir_refuses_dead_heir():
    s = _new(seed=77)
    _give_partner(s)
    genealogy.have_child(s, Rng(91).fork(7))
    heir_id = s.character.children[0]
    next(a for a in s.agents if a.npc_id == heir_id).alive = False
    s.mode = "DEATH"
    assert genealogy.continue_as_heir(s, heir_id) is False


def test_continue_as_heir_refuses_unrelated_npc():
    s = _new(seed=77)
    _give_partner(s)
    genealogy.have_child(s, Rng(94).fork(7))
    s.mode = "DEATH"
    # The partner is alive but isn't a child — must refuse.
    assert genealogy.continue_as_heir(s, 999) is False


# --- Persistence ---------------------------------------------------------


def test_ancestors_survive_save_load_roundtrip():
    s = _new(seed=42)
    _give_partner(s)
    genealogy.have_child(s, Rng(101).fork(7))
    heir_id = s.character.children[0]
    s.mode = "DEATH"
    s.money = 10_000
    genealogy.continue_as_heir(s, heir_id)
    assert s.ancestors
    rebuilt = GameState.from_dict(s.to_dict())
    assert rebuilt.ancestors == s.ancestors


# --- Controller verb -----------------------------------------------------


def test_controller_continue_as_heir_no_ops_outside_death():
    """Defensive: the controller must not crash if the UI somehow calls
    continueAsHeir when the player is still alive."""
    c = GameController()
    c.new_game(seed=5, name="", gender="Male", country="US", talent="Sports")
    snap = c.continue_as_heir(123)
    assert snap["mode"] == "PLAYING"
    assert snap["character"]["age"] == 0  # untouched
