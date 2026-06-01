"""Pregnancy v1 — conception → one-tick gestation → birth → naming.

Covers: begin_pregnancy (guaranteed path), attempt_conception (probabilistic
path, age + health gates), resolve_pregnancy in age_up, miscarriage roll,
two-parent genetic inheritance, the naming flow, and the integration with
existing consider_child / heir-transition / save-load systems.
"""
from __future__ import annotations

import pytest

from controller.game_controller import GameController
from core import events as event_engine, genealogy, sim
from core.predicates import IsPregnant
from core.rng import Rng
from core.state import GameState, PregnancyState, Relationship


def _new(seed: int = 1) -> GameState:
    return sim.new_game(seed=seed, name="", gender="Female", country="US", talent="Sports")


def _give_partner(s: GameState, npc_id: int = 999, age: int = 28,
                  looks: int = 80, smarts: int = 80) -> None:
    from core.agents import Agent
    s.relationships.append(Relationship(
        npc_id=npc_id, name="Alex Partner", kind="Partner",
        relationship=80, alive=True,
    ))
    s.agents.append(Agent(
        npc_id=npc_id, first_name="Alex", last_name="Partner",
        gender="Male", role="Partner", age=age,
        country=s.character.country if s.character else "US",
        city=s.character.city if s.character else "",
        looks=looks, smarts=smarts,
    ))


# --- begin_pregnancy (guaranteed path) ------------------------------------


def test_begin_pregnancy_registers_state_and_snapshots_partner_stats():
    s = _new()
    _give_partner(s, looks=90, smarts=70)
    ok = genealogy.begin_pregnancy(s)
    assert ok is True
    assert s.pregnancy.is_active is True
    assert s.pregnancy.conception_age == s.character.age
    # Partner stats frozen at conception so post-conception drift can't
    # change the inherited genes at birth.
    assert s.pregnancy.partner_looks == 90
    assert s.pregnancy.partner_smarts == 70


def test_begin_pregnancy_refuses_without_partner():
    s = _new()
    assert genealogy.begin_pregnancy(s) is False
    assert s.pregnancy.is_active is False


def test_begin_pregnancy_refuses_when_already_pregnant():
    s = _new()
    _give_partner(s)
    genealogy.begin_pregnancy(s)
    ok = genealogy.begin_pregnancy(s)
    assert ok is False


# --- attempt_conception (probabilistic) -----------------------------------


def test_attempt_conception_refuses_outside_fertility_band():
    s = _new()
    _give_partner(s)
    s.character.age = 14
    ok = genealogy.attempt_conception(s, Rng(1).fork(7))
    assert ok is False
    s.character.age = 60
    ok = genealogy.attempt_conception(s, Rng(2).fork(7))
    assert ok is False


def test_attempt_conception_can_succeed_in_young_band():
    """Across enough seeds with a young, healthy carrier and a partner,
    the probabilistic path must succeed at least sometimes."""
    s = _new()
    _give_partner(s)
    s.character.age = 24
    s.stats.health = 100
    successes = 0
    for seed in range(20):
        s2 = _new(seed=seed)
        _give_partner(s2)
        s2.character.age = 24
        s2.stats.health = 100
        if genealogy.attempt_conception(s2, Rng(seed + 10_000).fork(7)):
            successes += 1
    assert successes > 0


def test_attempt_conception_refuses_when_already_pregnant():
    s = _new()
    _give_partner(s)
    genealogy.begin_pregnancy(s)
    # Even with favourable rolls, no double-registering.
    for seed in range(10):
        ok = genealogy.attempt_conception(s, Rng(seed).fork(7))
        assert ok is False


# --- resolve_pregnancy (gestation cycle) ----------------------------------


def test_resolve_pregnancy_skips_when_no_active_pregnancy():
    s = _new()
    result = genealogy.resolve_pregnancy(s, Rng(1).fork(7))
    assert result is None


def test_resolve_pregnancy_skips_on_same_tick_as_conception():
    """Same-tick resolution would mean a baby appears the moment the
    player clicked 'try'. Gestation must take at least one age_up."""
    s = _new()
    _give_partner(s)
    genealogy.begin_pregnancy(s)
    # tick hasn't advanced — must no-op.
    assert genealogy.resolve_pregnancy(s, Rng(1).fork(7)) is None
    assert s.pregnancy.is_active is True


def test_resolve_pregnancy_births_a_child_on_subsequent_tick():
    s = _new()
    _give_partner(s, looks=80, smarts=80)
    genealogy.begin_pregnancy(s)
    s.tick += 1  # simulate the next age_up
    # Use a seed range where miscarriage doesn't fire (5% prob).
    for seed in range(20):
        s2 = _new()
        _give_partner(s2)
        genealogy.begin_pregnancy(s2)
        s2.tick += 1
        result = genealogy.resolve_pregnancy(s2, Rng(seed).fork(7))
        if result is not None:
            # Healthy birth: pending_birth set, child in agents, pregnancy cleared.
            assert s2.pregnancy.is_active is False
            assert s2.pending_birth is not None
            assert s2.pending_birth["npc_id"] in s2.character.children
            child_agent = next(a for a in s2.agents if a.npc_id == s2.pending_birth["npc_id"])
            assert child_agent.age == 0
            return  # one successful seed is enough
    pytest.fail("no seed in range produced a healthy birth — check miscarriage prob")


def test_resolve_pregnancy_miscarriage_clears_state_and_writes_feed():
    """Force a miscarriage by using a seed that lands inside the 5% prob.
    Just iterating until rng.chance(0.05) succeeds gives us coverage."""
    for seed in range(200):
        s = _new()
        _give_partner(s)
        genealogy.begin_pregnancy(s)
        s.tick += 1
        before_happiness = s.stats.happiness
        genealogy.resolve_pregnancy(s, Rng(seed).fork(7))
        if not s.character.children and s.pending_birth is None:
            # Miscarriage path: pregnancy cleared, happiness dropped, feed entry written.
            assert s.pregnancy.is_active is False
            assert s.stats.happiness < before_happiness
            assert any(e.entry_id.startswith("feed:miscarriage:") for e in s.feed)
            return
    pytest.fail("no seed in range triggered a miscarriage — check the prob")


# --- Genetic inheritance --------------------------------------------------


def test_child_stats_blend_from_both_parents():
    """Two high-stat parents produce a high-stat child; two low-stat
    parents produce a low-stat one. Confirms the partner's stats are
    actually consulted instead of the old midpoint fallback."""
    high_avg = []
    low_avg = []
    for seed in range(10):
        s_hi = _new(seed=seed)
        _give_partner(s_hi, looks=100, smarts=100)
        s_hi.stats.smarts = 100
        s_hi.stats.looks = 100
        genealogy.begin_pregnancy(s_hi)
        s_hi.tick += 1
        result = genealogy.resolve_pregnancy(s_hi, Rng(seed + 1_000).fork(7))
        if result is None:
            continue
        kid = next(a for a in s_hi.agents if a.npc_id == result["npc_id"])
        high_avg.append((kid.looks + kid.smarts) / 2)

        s_lo = _new(seed=seed)
        _give_partner(s_lo, looks=10, smarts=10)
        s_lo.stats.smarts = 10
        s_lo.stats.looks = 10
        genealogy.begin_pregnancy(s_lo)
        s_lo.tick += 1
        result2 = genealogy.resolve_pregnancy(s_lo, Rng(seed + 2_000).fork(7))
        if result2 is None:
            continue
        kid2 = next(a for a in s_lo.agents if a.npc_id == result2["npc_id"])
        low_avg.append((kid2.looks + kid2.smarts) / 2)

    assert high_avg and low_avg, "needed at least one healthy birth per band"
    # Children of 100/100 parents must average higher than children of
    # 10/10 parents. Jitter is ±10 so the bands can't realistically overlap.
    assert sum(high_avg) / len(high_avg) > sum(low_avg) / len(low_avg) + 40


# --- Naming flow ----------------------------------------------------------


def test_name_child_updates_agent_relationship_and_feed():
    s = _new()
    _give_partner(s)
    genealogy.begin_pregnancy(s)
    s.tick += 1
    # Find a seed that lands a healthy birth.
    for seed in range(20):
        s2 = _new()
        _give_partner(s2)
        genealogy.begin_pregnancy(s2)
        s2.tick += 1
        result = genealogy.resolve_pregnancy(s2, Rng(seed).fork(7))
        if result is None:
            continue
        old_first = result["suggested_name"]
        npc_id = result["npc_id"]
        ok = genealogy.name_child(s2, npc_id, "Echo")
        assert ok is True
        assert s2.pending_birth is None
        # Agent + Relationship + feed all reflect the new name.
        agent = next(a for a in s2.agents if a.npc_id == npc_id)
        rel = next(r for r in s2.relationships if r.npc_id == npc_id)
        assert agent.first_name == "Echo"
        assert "Echo" in rel.name
        feed_text = " ".join(e.text for e in s2.feed)
        assert "Echo" in feed_text
        assert old_first not in feed_text or old_first == "Echo"
        return
    pytest.fail("no healthy birth in seed range")


def test_name_child_refuses_blank_or_wrong_npc():
    s = _new()
    s.pending_birth = {
        "npc_id": 7, "gender": "Male", "suggested_name": "Bob", "last_name": "X",
        "partner_name": "Alex",
    }
    assert genealogy.name_child(s, 7, "   ") is False
    assert genealogy.name_child(s, 999, "Lou") is False  # wrong npc_id
    assert s.pending_birth is not None  # nothing cleared on refusal


# --- Predicate ------------------------------------------------------------


def test_is_pregnant_predicate_flips_with_state():
    s = _new()
    _give_partner(s)
    assert IsPregnant()(s) is False
    genealogy.begin_pregnancy(s)
    assert IsPregnant()(s) is True


# --- Sim integration ------------------------------------------------------


def test_age_up_resolves_pregnancy_during_tick():
    """End-to-end: register a pregnancy, call sim.age_up, and the next
    year's tick must either birth a baby (pending_birth set) or write a
    miscarriage entry — never leave the pregnancy active."""
    s = _new(seed=99)
    _give_partner(s)
    s.character.age = 24
    genealogy.begin_pregnancy(s)
    assert s.pregnancy.is_active is True
    sim.age_up(s)
    assert s.pregnancy.is_active is False
    # Either path is fine; both clear the pregnancy.
    miscarriage = any(e.entry_id.startswith("feed:miscarriage:") for e in s.feed)
    healthy = s.pending_birth is not None
    assert miscarriage or healthy


# --- Save / load ---------------------------------------------------------


def test_pregnancy_state_roundtrips_through_save_load():
    s = _new()
    _give_partner(s, looks=77, smarts=33)
    genealogy.begin_pregnancy(s)
    rebuilt = GameState.from_dict(s.to_dict())
    assert rebuilt.pregnancy.is_active is True
    assert rebuilt.pregnancy.partner_looks == 77
    assert rebuilt.pregnancy.partner_smarts == 33
    assert rebuilt.pregnancy.conception_age == s.pregnancy.conception_age


def test_pending_birth_roundtrips_through_save_load():
    s = _new()
    s.pending_birth = {"npc_id": 5, "gender": "Female", "suggested_name": "A",
                       "last_name": "B", "partner_name": "C"}
    rebuilt = GameState.from_dict(s.to_dict())
    assert rebuilt.pending_birth == s.pending_birth


# --- Heir transition reset ------------------------------------------------


def test_continue_as_heir_clears_pregnancy_and_pending_birth():
    """A new generation can't inherit the deceased's gestation state —
    that'd cause a phantom pregnancy on the heir's first tick."""
    s = _new(seed=42)
    _give_partner(s)
    genealogy.begin_pregnancy(s)
    # Force a birth so there's a child to continue as.
    s.tick += 1
    for seed in range(20):
        s_try = _new(seed=42)
        _give_partner(s_try)
        genealogy.begin_pregnancy(s_try)
        s_try.tick += 1
        if genealogy.resolve_pregnancy(s_try, Rng(seed).fork(7)) is not None:
            s = s_try
            break
    heir_id = s.character.children[0]
    # Register a new pregnancy on the dying parent.
    genealogy.begin_pregnancy(s)
    s.pending_birth = {"npc_id": 999, "gender": "Male", "suggested_name": "X",
                       "last_name": "Y", "partner_name": "Z"}
    s.mode = "DEATH"
    genealogy.continue_as_heir(s, heir_id)
    assert s.pregnancy.is_active is False
    assert s.pending_birth is None


# --- Controller verbs ---------------------------------------------------


def test_controller_try_for_baby_writes_to_feed():
    c = GameController()
    c.new_game(seed=8, name="", gender="Female", country="US", talent="Sports")
    _give_partner(c.state)
    c.state.character.age = 25
    snap = c.try_for_baby()
    feed_text = " ".join(e["text"] for e in snap["feed"])
    assert "tried" in feed_text.lower() or "trying" in feed_text.lower()


def test_controller_name_baby_clears_pending_birth():
    c = GameController()
    c.new_game(seed=15, name="", gender="Female", country="US", talent="Sports")
    _give_partner(c.state)
    c.state.character.age = 26
    genealogy.begin_pregnancy(c.state)
    c.age_up()  # gestation tick
    # Find a seed-state that landed a healthy birth, or build one directly.
    if c.snapshot()["pending_birth"] is None:
        # Force the birth side of resolve so this isn't flaky.
        c.state.pending_birth = {"npc_id": 1234, "gender": "Male",
                                 "suggested_name": "Default", "last_name": "Test",
                                 "partner_name": "Alex"}
        from core.agents import Agent
        c.state.agents.append(Agent(
            npc_id=1234, first_name="Default", last_name="Test",
            gender="Male", role="Child", age=0, country="US", city="",
        ))
    snap = c.name_baby(c.state.pending_birth["npc_id"], "Atlas")
    assert snap["pending_birth"] is None
