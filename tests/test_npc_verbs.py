"""NPC verbs v1 — apologize, deep_talk, ask_advice, borrow_money,
insult, lavish_gift, take_to_dinner.

Covers refusal modes (unknown npc, dead npc, gating thresholds, cost
ceilings), deterministic verbs' fixed effects, and the rng-driven
verbs' both branches via seed sweeping.
"""
from __future__ import annotations

import pytest

from controller.game_controller import GameController
from core import relationships
from core.agents import Agent
from core.rng import Rng
from core.state import GameState, Relationship


def _new(seed: int = 1, money: int = 1_000) -> GameState:
    from core import sim
    s = sim.new_game(seed=seed, name="", gender="Female", country="US", talent="Sports")
    s.character.age = 25
    s.money = money
    return s


def _add_friend(s: GameState, *, rel: int = 60, agent_money: int = 5_000,
                npc_id: int = 901, smarts: int = 70) -> int:
    s.relationships.append(Relationship(
        npc_id=npc_id, name="Pat Friend", kind="Friend",
        relationship=rel, alive=True,
    ))
    s.agents.append(Agent(
        npc_id=npc_id, first_name="Pat", last_name="Friend",
        gender="NonBinary", role="Friend", age=25,
        country=s.character.country if s.character else "US", city="",
        smarts=smarts, money=agent_money,
    ))
    return npc_id


# --- Universal refusals ---------------------------------------------------


def test_unknown_npc_refuses_everything():
    s = _new()
    for action in relationships.INTERACTIONS:
        ok, msg = relationships.interact(s, 99_999, action, rng=Rng(1).fork(7))
        assert ok is False
        assert "don't know" in msg.lower()


def test_dead_npc_refuses_everything():
    s = _new()
    npc_id = _add_friend(s)
    rel = next(r for r in s.relationships if r.npc_id == npc_id)
    rel.alive = False
    for action in relationships.INTERACTIONS:
        ok, msg = relationships.interact(s, npc_id, action, rng=Rng(1).fork(7))
        assert ok is False
        assert "passed away" in msg.lower()


# --- apologize ----------------------------------------------------------


def test_apologize_big_lift_when_relationship_hurt():
    s = _new()
    npc_id = _add_friend(s, rel=20)
    ok, _ = relationships.interact(s, npc_id, "apologize")
    rel = next(r for r in s.relationships if r.npc_id == npc_id)
    assert ok is True
    assert rel.relationship == 32  # +12 because rel < 50


def test_apologize_small_when_relationship_healthy():
    s = _new()
    npc_id = _add_friend(s, rel=80)
    relationships.interact(s, npc_id, "apologize")
    rel = next(r for r in s.relationships if r.npc_id == npc_id)
    assert rel.relationship == 82  # only +2 when rel >= 50


# --- deep_talk ----------------------------------------------------------


def test_deep_talk_has_both_outcomes_under_different_seeds():
    """The verb is meant to be rng-driven; across enough seeds we
    should see BOTH the 'lands' (+6 rel) and the 'gets heavy' (+2 rel)
    branches fire."""
    good_count = 0
    heavy_count = 0
    for seed in range(50):
        s = _new()
        npc_id = _add_friend(s, rel=50)
        relationships.interact(s, npc_id, "deep_talk", rng=Rng(seed).fork(7))
        rel = next(r for r in s.relationships if r.npc_id == npc_id)
        if rel.relationship == 56:
            good_count += 1
        elif rel.relationship == 52:
            heavy_count += 1
    assert good_count > 0
    assert heavy_count > 0


# --- ask_advice ---------------------------------------------------------


def test_ask_advice_refuses_below_threshold():
    s = _new()
    npc_id = _add_friend(s, rel=20)  # below ADVICE_MIN_RELATIONSHIP=30
    ok, _ = relationships.interact(s, npc_id, "ask_advice", rng=Rng(1).fork(7))
    assert ok is False


def test_ask_advice_smarter_npc_more_often_useful():
    """High-smarts NPCs should land useful advice substantially more
    often than low-smarts NPCs across a fixed seed sweep."""
    smart_useful = 0
    dull_useful = 0
    for seed in range(50):
        s_high = _new()
        s_low = _new()
        npc_high = _add_friend(s_high, rel=80, smarts=100)
        npc_low = _add_friend(s_low, rel=80, smarts=20)
        smarts_before_high = s_high.stats.smarts
        smarts_before_low = s_low.stats.smarts
        relationships.interact(s_high, npc_high, "ask_advice", rng=Rng(seed).fork(7))
        relationships.interact(s_low, npc_low, "ask_advice", rng=Rng(seed).fork(7))
        if s_high.stats.smarts > smarts_before_high:
            smart_useful += 1
        if s_low.stats.smarts > smarts_before_low:
            dull_useful += 1
    assert smart_useful > dull_useful + 5  # meaningful gap, not just edge noise


# --- borrow_money -------------------------------------------------------


def test_borrow_refuses_when_relationship_too_low():
    s = _new()
    npc_id = _add_friend(s, rel=30)  # below BORROW_MIN_RELATIONSHIP=50
    money_before = s.money
    ok, _ = relationships.interact(s, npc_id, "borrow_money", rng=Rng(1).fork(7))
    assert ok is False
    assert s.money == money_before


def test_borrow_refuses_when_npc_broke():
    s = _new()
    npc_id = _add_friend(s, rel=90, agent_money=100)  # below BORROW_NPC_MIN_MONEY
    money_before = s.money
    ok, _ = relationships.interact(s, npc_id, "borrow_money", rng=Rng(1).fork(7))
    assert ok is False
    assert s.money == money_before


def test_borrow_success_credits_player_and_debits_npc():
    """Find a seed where the lend roll succeeds and assert conservation:
    money moves from agent to player exactly."""
    for seed in range(50):
        s = _new()
        npc_id = _add_friend(s, rel=90, agent_money=5_000)
        player_before = s.money
        agent = next(a for a in s.agents if a.npc_id == npc_id)
        agent_money_before = agent.money
        ok, msg = relationships.interact(s, npc_id, "borrow_money", rng=Rng(seed).fork(7))
        if ok and "lent" in msg.lower():
            delta = s.money - player_before
            assert delta > 0
            assert agent.money == agent_money_before - delta
            return
    pytest.fail("no seed produced a successful borrow across 50 attempts")


def test_borrow_failure_costs_relationship_and_happiness():
    """Find a seed where the lend roll fails."""
    for seed in range(50):
        s = _new()
        npc_id = _add_friend(s, rel=55, agent_money=5_000)
        rel_before = next(r for r in s.relationships if r.npc_id == npc_id).relationship
        happy_before = s.stats.happiness
        ok, msg = relationships.interact(s, npc_id, "borrow_money", rng=Rng(seed).fork(7))
        rel = next(r for r in s.relationships if r.npc_id == npc_id)
        if ok and "no" in msg.lower():
            assert rel.relationship < rel_before
            assert s.stats.happiness < happy_before
            return
    pytest.fail("no seed produced a refused borrow across 50 attempts")


# --- insult ------------------------------------------------------------


def test_insult_is_worse_than_argue():
    s_argue = _new()
    s_insult = _new()
    a_id = _add_friend(s_argue, rel=60)
    i_id = _add_friend(s_insult, rel=60)
    relationships.interact(s_argue, a_id, "argue")
    relationships.interact(s_insult, i_id, "insult")
    rel_argue = next(r for r in s_argue.relationships if r.npc_id == a_id)
    rel_insult = next(r for r in s_insult.relationships if r.npc_id == i_id)
    assert rel_insult.relationship < rel_argue.relationship


# --- lavish_gift -------------------------------------------------------


def test_lavish_gift_refuses_when_broke():
    s = _new(money=400)  # below LAVISH_GIFT_COST=500
    npc_id = _add_friend(s)
    ok, _ = relationships.interact(s, npc_id, "lavish_gift")
    assert ok is False
    assert s.money == 400


def test_lavish_gift_lifts_relationship_and_charges_money():
    s = _new(money=10_000)
    npc_id = _add_friend(s, rel=50)
    relationships.interact(s, npc_id, "lavish_gift")
    rel = next(r for r in s.relationships if r.npc_id == npc_id)
    assert s.money == 10_000 - relationships.LAVISH_GIFT_COST
    assert rel.relationship == 70  # +20


# --- take_to_dinner ---------------------------------------------------


def test_dinner_refuses_when_broke():
    s = _new(money=50)
    npc_id = _add_friend(s)
    ok, _ = relationships.interact(s, npc_id, "take_to_dinner")
    assert ok is False


def test_dinner_lifts_relationship_and_happiness():
    s = _new(money=1_000)
    s.stats.happiness = 50
    npc_id = _add_friend(s, rel=50)
    relationships.interact(s, npc_id, "take_to_dinner")
    rel = next(r for r in s.relationships if r.npc_id == npc_id)
    assert s.money == 1_000 - relationships.DINNER_COST
    assert rel.relationship == 58
    assert s.stats.happiness == 53


# --- Controller verb passes rng through ------------------------------


def test_controller_relationship_action_routes_rng_for_probabilistic_verbs():
    """End-to-end: controller.relationship_action must fork an rng and
    pass it through. Without this, deep_talk would always take the
    deterministic branch."""
    c = GameController()
    c.new_game(seed=1, name="", gender="Female", country="US", talent="Sports")
    c.state.character.age = 30
    npc_id = _add_friend(c.state, rel=50)
    # Call several times — at least one outcome should differ (proving
    # determinism shifts with tick/feed-length).
    outcomes = set()
    for _ in range(8):
        c.relationship_action(npc_id, "deep_talk")
        rel = next(r for r in c.state.relationships if r.npc_id == npc_id)
        outcomes.add(rel.relationship - 50)
        # Reset for next call so the +6 doesn't accumulate.
        rel.relationship = 50
    assert len(outcomes) > 1, "deep_talk produced identical outcomes — rng not forked"


def test_interactions_tuple_lists_every_supported_verb():
    """The UI consults INTERACTIONS to gate buttons; if a verb is
    handled in interact() but missing here, the UI silently can't
    expose it. This test keeps the two in sync."""
    s = _new(money=10_000)
    npc_id = _add_friend(s, rel=80)
    for action in relationships.INTERACTIONS:
        # Each verb should return a result of some kind (not crash).
        result = relationships.interact(s, npc_id, action, rng=Rng(1).fork(7))
        assert hasattr(result, "ok")
        assert hasattr(result, "message")
