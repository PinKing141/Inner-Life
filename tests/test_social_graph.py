"""Phase 2 — NPC↔NPC social graph.

Tests for the new ``core/social.py`` module: edge primitives (add/remove/
query/canonicalisation), initial seeding (parent spouse + family friends),
persistence round-trip, the ``RelativeHasEmployedFriend`` predicate, and
the demonstrating ``family_friend_referral`` event firing end-to-end.
"""
from __future__ import annotations

import pytest

from controller.game_controller import GameController
from core import agents, sim, social
from core.predicates import RelativeHasEmployedFriend
from core.state import GameState, Job


def _new(seed: int = 1) -> GameState:
    return sim.new_game(seed=seed, name="", gender="Female", country="US", talent="Sports")


# --- Edge primitives -------------------------------------------------------


def test_edges_are_canonicalised_smaller_id_first():
    s = _new()
    e = social.add_edge(s, 9, 4, "friend")
    assert (e.a, e.b) == (4, 9)


def test_add_edge_is_idempotent_and_overwrites():
    s = _new()
    social.add_edge(s, 1, 2, "friend", strength=40)
    social.add_edge(s, 1, 2, "rival", strength=80)
    edges = [e for e in s.social_edges if e.involves(1) and e.involves(2)]
    assert len(edges) == 1
    assert edges[0].kind == "rival"
    assert edges[0].strength == 80


def test_self_loop_is_rejected():
    s = _new()
    with pytest.raises(ValueError):
        social.add_edge(s, 5, 5, "friend")


def test_remove_edge_returns_whether_removed():
    s = _new()
    social.add_edge(s, 10, 20, "friend")
    assert social.remove_edge(s, 20, 10) is True
    assert social.remove_edge(s, 20, 10) is False


def test_remove_edges_of_drops_every_edge_touching_id():
    s = _new()
    s.social_edges.clear()  # work on a blank graph
    social.add_edge(s, 1, 2, "friend")
    social.add_edge(s, 1, 3, "friend")
    social.add_edge(s, 2, 3, "rival")
    removed = social.remove_edges_of(s, 1)
    assert removed == 2
    assert social.get_edge(s, 2, 3) is not None
    assert social.get_edge(s, 1, 2) is None


def test_neighbors_returns_stable_sorted_other_endpoints():
    s = _new()
    s.social_edges.clear()
    social.add_edge(s, 5, 7, "friend")
    social.add_edge(s, 5, 3, "friend")
    social.add_edge(s, 9, 5, "rival")
    assert social.neighbors(s, 5) == [3, 7, 9]
    assert social.neighbors(s, 5, kind="friend") == [3, 7]


def test_mutual_neighbors_finds_triangle_completers():
    s = _new()
    s.social_edges.clear()
    # Triangle: 1—10, 2—10 (10 is the shared friend of 1 and 2)
    social.add_edge(s, 1, 10, "friend")
    social.add_edge(s, 2, 10, "friend")
    # Plus a non-triangle: 1—11 only
    social.add_edge(s, 1, 11, "friend")
    assert social.mutual_neighbors(s, 1, 2) == [10]


def test_are_connected_respects_kind_filter():
    s = _new()
    s.social_edges.clear()
    social.add_edge(s, 1, 2, "friend")
    assert social.are_connected(s, 2, 1) is True
    assert social.are_connected(s, 2, 1, kind="friend") is True
    assert social.are_connected(s, 2, 1, kind="rival") is False


def test_bump_strength_clamps_and_noops_when_missing():
    s = _new()
    s.social_edges.clear()
    e = social.add_edge(s, 1, 2, "friend", strength=95)
    social.bump_strength(s, 1, 2, 20)
    assert e.strength == 100  # clamped
    social.bump_strength(s, 1, 2, -150)
    assert e.strength == 0    # clamped low
    assert social.bump_strength(s, 1, 99, 10) is None


# --- Seeding & determinism ------------------------------------------------


def test_parents_are_seeded_as_spouses():
    s = _new()
    mother = next(a for a in s.agents if a.role == "Mother")
    father = next(a for a in s.agents if a.role == "Father")
    assert social.are_connected(s, mother.npc_id, father.npc_id, kind="spouse")


def test_each_parent_gets_at_least_one_employed_friend():
    s = _new()
    agent_by_id = {a.npc_id: a for a in s.agents}
    for kind in ("Mother", "Father"):
        parent = next(a for a in s.agents if a.role == kind)
        friend_ids = social.neighbors(s, parent.npc_id, kind="friend")
        assert friend_ids, f"{kind} should have at least one friend NPC"
        assert any(agent_by_id[i].job_title for i in friend_ids), (
            f"{kind}'s friend circle must include at least one employed NPC"
        )


def test_family_friends_are_NOT_in_player_relationships():
    """The graph layer is broader than the player's known relationships;
    parents' friends must NOT appear as direct ties."""
    s = _new()
    mother = next(a for a in s.agents if a.role == "Mother")
    friend_ids = set(social.neighbors(s, mother.npc_id, kind="friend"))
    rel_ids = {r.npc_id for r in s.relationships}
    assert friend_ids.isdisjoint(rel_ids)


def test_seeding_is_deterministic_same_seed_same_graph():
    a = _new(seed=42)
    b = _new(seed=42)
    assert [e.to_dict() for e in a.social_edges] == [e.to_dict() for e in b.social_edges]


def test_seeding_differs_across_seeds():
    a = _new(seed=1)
    b = _new(seed=2)
    assert [e.to_dict() for e in a.social_edges] != [e.to_dict() for e in b.social_edges]


# --- Persistence -----------------------------------------------------------


def test_social_edges_survive_save_load_roundtrip():
    s = _new(seed=99)
    before = [e.to_dict() for e in s.social_edges]
    rebuilt = GameState.from_dict(s.to_dict())
    after = [e.to_dict() for e in rebuilt.social_edges]
    assert before == after


def test_from_dict_recanonicalises_reversed_edges():
    """A defensive parser: even if an older save wrote (b, a) instead of
    (a, b), reloading should canonicalise so subsequent queries work."""
    s = _new()
    s.social_edges.clear()
    raw = s.to_dict()
    raw["social_edges"] = [{"a": 9, "b": 2, "kind": "friend", "strength": 50}]
    rebuilt = GameState.from_dict(raw)
    assert rebuilt.social_edges[0].a == 2
    assert rebuilt.social_edges[0].b == 9


# --- Predicate -------------------------------------------------------------


def test_relative_has_employed_friend_is_true_at_birth():
    s = _new()
    assert RelativeHasEmployedFriend("Mother")(s) is True


def test_predicate_false_when_no_relative_of_kind():
    s = _new()
    s.relationships = [r for r in s.relationships if r.kind != "Mother"]
    assert RelativeHasEmployedFriend("Mother")(s) is False


def test_predicate_false_when_friend_is_unemployed():
    s = _new()
    mother = next(a for a in s.agents if a.role == "Mother")
    for nb_id in social.neighbors(s, mother.npc_id, kind="friend"):
        friend = next(a for a in s.agents if a.npc_id == nb_id)
        friend.job_title = None
    assert RelativeHasEmployedFriend("Mother")(s) is False


def test_predicate_false_when_friend_is_dead():
    s = _new()
    mother = next(a for a in s.agents if a.role == "Mother")
    for nb_id in social.neighbors(s, mother.npc_id, kind="friend"):
        friend = next(a for a in s.agents if a.npc_id == nb_id)
        friend.alive = False
    assert RelativeHasEmployedFriend("Mother")(s) is False


# --- Demo event end-to-end ------------------------------------------------


def test_family_friend_referral_event_mints_a_career():
    """Resolving the demo event's 'yes' choice must populate state.career
    using a friend's job_title — the side-effect reads from the graph."""
    c = GameController()
    c.new_game(seed=7, name="", gender="Female", country="US", talent="Academics")
    c.state.character.age = 22
    c.state.career = None  # ensure unemployed
    # Fire the event directly through the engine so we don't rely on
    # probability to surface it in this test.
    from core import events as engine
    ev = engine.get_event("family_friend_referral")
    assert ev is not None
    c.state.pending_event_id = ev["id"]
    c.choose(0)  # "Yes — start there"
    assert c.state.career is not None
    assert c.state.career.job_id == "family_friend_referral"
    assert c.state.career.title.startswith("Junior ")


def test_family_friend_referral_decline_leaves_player_unemployed():
    c = GameController()
    c.new_game(seed=7, name="", gender="Female", country="US", talent="Academics")
    c.state.character.age = 22
    c.state.career = None
    from core import events as engine
    ev = engine.get_event("family_friend_referral")
    assert ev is not None
    c.state.pending_event_id = ev["id"]
    c.choose(1)  # "No — you'll find your own way"
    assert c.state.career is None


def test_referral_side_effect_no_ops_if_graph_drifted():
    """If between roll and resolve the friend died or lost their job, the
    side-effect should silently no-op rather than crash. Pin that
    behaviour."""
    c = GameController()
    c.new_game(seed=7, name="", gender="Female", country="US", talent="Academics")
    c.state.character.age = 22
    c.state.career = None
    # Drift: kill every family friend in the graph. The side-effect falls
    # back to the father's circle if the mother's is empty, so both must
    # be cleared to exercise the no-op branch.
    for kind in ("Mother", "Father"):
        parent_rel = next((r for r in c.state.relationships if r.kind == kind), None)
        if parent_rel is None:
            continue
        for nb_id in social.neighbors(c.state, parent_rel.npc_id, kind="friend"):
            ag = next(a for a in c.state.agents if a.npc_id == nb_id)
            ag.alive = False
    from core import events as engine
    ev = engine.get_event("family_friend_referral")
    assert ev is not None
    c.state.pending_event_id = ev["id"]
    c.choose(0)
    assert c.state.career is None  # silent no-op


# --- Forming new ties at runtime extends the graph ------------------------


def test_form_incidental_tie_may_link_into_existing_graph():
    """When a new friend NPC is minted, the helper sometimes also wires up
    an NPC↔NPC edge to another existing agent. Over many seeds at least one
    such link should form — confirming the graph densifies over time
    rather than staying a pure star around the player."""
    from core.rng import Rng

    saw_link = False
    for seed in range(50):
        s = _new(seed=seed)
        s.character.age = 25  # adult, jobless: triggers friend not coworker
        s.education.in_school = False
        s.career = None
        baseline_edges = len(s.social_edges)
        agents.form_incidental_ties(s, Rng(seed).fork(39))
        # If a new NPC was minted, we may have added 1 player↔NPC tie (no
        # graph edge; that lives in relationships) AND optionally a new
        # NPC↔NPC graph edge from the helper. Detect the latter.
        if len(s.social_edges) > baseline_edges:
            saw_link = True
            break
    assert saw_link, "incidental tie formation should sometimes add a graph edge"
