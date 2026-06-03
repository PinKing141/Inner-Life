"""NPC verbs v1 — talk/compliment/argue/apologize/conversation/ask_advice
/hang_out/give_gift/give_money/borrow_money/insult.

Covers refusal modes, deterministic verbs, rng-driven verbs (both
branches via seed sweep), and the picker verbs that take a ``param``
selecting a gift or money tier.
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
    relationships.interact(s, npc_id, "apologize")
    rel = next(r for r in s.relationships if r.npc_id == npc_id)
    assert rel.relationship == 32  # +12 because rel < 50


def test_apologize_small_when_relationship_healthy():
    s = _new()
    npc_id = _add_friend(s, rel=80)
    relationships.interact(s, npc_id, "apologize")
    rel = next(r for r in s.relationships if r.npc_id == npc_id)
    assert rel.relationship == 82  # only +2 when rel >= 50


# --- conversation (rng-driven) ------------------------------------------


def test_conversation_has_both_outcomes_under_different_seeds():
    good_count = 0
    heavy_count = 0
    for seed in range(50):
        s = _new()
        npc_id = _add_friend(s, rel=50)
        relationships.interact(s, npc_id, "conversation", rng=Rng(seed).fork(7))
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
    npc_id = _add_friend(s, rel=20)
    ok, _ = relationships.interact(s, npc_id, "ask_advice", rng=Rng(1).fork(7))
    assert ok is False


def test_ask_advice_smarter_npc_more_often_useful():
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
    assert smart_useful > dull_useful + 5


# --- hang_out ----------------------------------------------------------


def test_hang_out_is_free_and_lifts_relationship_and_happiness():
    s = _new(money=0)
    s.stats.happiness = 50
    npc_id = _add_friend(s, rel=50)
    ok, _ = relationships.interact(s, npc_id, "hang_out")
    rel = next(r for r in s.relationships if r.npc_id == npc_id)
    assert ok is True
    assert s.money == 0  # free
    assert rel.relationship == 55
    assert s.stats.happiness == 53


# --- give_gift (picker) ------------------------------------------------


def test_give_gift_without_param_refuses():
    s = _new()
    npc_id = _add_friend(s)
    ok, _ = relationships.interact(s, npc_id, "give_gift", param=None)
    assert ok is False


def test_give_gift_unknown_id_refuses():
    s = _new()
    npc_id = _add_friend(s)
    ok, _ = relationships.interact(s, npc_id, "give_gift", param="rocket_ship")
    assert ok is False


def test_give_gift_free_option_works_when_broke():
    """The free handmade card is the inclusivity option — no money path
    should still produce a real relationship lift."""
    s = _new(money=0)
    npc_id = _add_friend(s, rel=50)
    ok, _ = relationships.interact(s, npc_id, "give_gift", param="handmade_card")
    rel = next(r for r in s.relationships if r.npc_id == npc_id)
    assert ok is True
    assert s.money == 0
    assert rel.relationship == 53  # +3 boost from the catalogue


def test_give_gift_paid_option_debits_money_and_lifts_relationship():
    s = _new(money=10_000)
    npc_id = _add_friend(s, rel=50)
    relationships.interact(s, npc_id, "give_gift", param="watch")
    rel = next(r for r in s.relationships if r.npc_id == npc_id)
    watch = next(g for g in relationships.GIFTS if g["id"] == "watch")
    assert s.money == 10_000 - watch["price"]
    assert rel.relationship == 50 + watch["rel_boost"]


def test_give_gift_refuses_when_broke():
    s = _new(money=100)
    npc_id = _add_friend(s)
    ok, _ = relationships.interact(s, npc_id, "give_gift", param="luxury_jewellery")
    assert ok is False
    assert s.money == 100  # untouched on refusal


def test_gift_catalogue_priced_in_ladder_order():
    """The catalogue is declared cheap → expensive so the UI can render
    it in that order without sorting. Stays useful as future entries
    are added."""
    prices = [g["price"] for g in relationships.GIFTS]
    assert prices == sorted(prices)


# --- give_money (picker) ------------------------------------------------


def test_give_money_without_param_refuses():
    s = _new()
    npc_id = _add_friend(s)
    ok, _ = relationships.interact(s, npc_id, "give_money", param=None)
    assert ok is False


def test_give_money_unknown_tier_refuses():
    s = _new()
    npc_id = _add_friend(s)
    ok, _ = relationships.interact(s, npc_id, "give_money", param="zillion")
    assert ok is False


def test_give_money_refuses_when_broke():
    s = _new(money=10)
    npc_id = _add_friend(s)
    ok, _ = relationships.interact(s, npc_id, "give_money", param="small")
    assert ok is False


def test_give_money_transfers_to_npc_with_conservation():
    """Player gives £500 → player.money -500, npc.money +500. Real
    money conservation (modelled as an Agent.money mutation)."""
    s = _new(money=10_000)
    npc_id = _add_friend(s, rel=50, agent_money=1_000)
    player_before = s.money
    agent = next(a for a in s.agents if a.npc_id == npc_id)
    agent_before = agent.money
    relationships.interact(s, npc_id, "give_money", param="medium")
    medium = next(t for t in relationships.MONEY_GIFTS if t["id"] == "medium")
    assert s.money == player_before - medium["amount"]
    assert agent.money == agent_before + medium["amount"]
    rel = next(r for r in s.relationships if r.npc_id == npc_id)
    assert rel.relationship == 50 + medium["rel_boost"]


def test_money_gift_tiers_in_ascending_order():
    amounts = [t["amount"] for t in relationships.MONEY_GIFTS]
    assert amounts == sorted(amounts)


# --- borrow_money -------------------------------------------------------


def test_borrow_refuses_when_relationship_too_low():
    s = _new()
    npc_id = _add_friend(s, rel=30)
    money_before = s.money
    ok, _ = relationships.interact(s, npc_id, "borrow_money", rng=Rng(1).fork(7))
    assert ok is False
    assert s.money == money_before


def test_borrow_refuses_when_npc_broke():
    s = _new()
    npc_id = _add_friend(s, rel=90, agent_money=100)
    money_before = s.money
    ok, _ = relationships.interact(s, npc_id, "borrow_money", rng=Rng(1).fork(7))
    assert ok is False
    assert s.money == money_before


def test_borrow_success_credits_player_and_debits_npc():
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


# --- Controller verb passes rng + param through ----------------------


def test_controller_routes_rng_for_probabilistic_verbs():
    c = GameController()
    c.new_game(seed=1, name="", gender="Female", country="US", talent="Sports")
    c.state.character.age = 30
    npc_id = _add_friend(c.state, rel=50)
    outcomes = set()
    for _ in range(8):
        c.relationship_action(npc_id, "conversation")
        rel = next(r for r in c.state.relationships if r.npc_id == npc_id)
        outcomes.add(rel.relationship - 50)
        rel.relationship = 50  # reset between calls
    assert len(outcomes) > 1, "conversation produced identical outcomes — rng not forked"


def test_controller_routes_param_for_give_gift():
    c = GameController()
    c.new_game(seed=1, name="", gender="Female", country="US", talent="Sports")
    c.state.character.age = 30
    c.state.money = 10_000
    npc_id = _add_friend(c.state, rel=50)
    c.relationship_action(npc_id, "give_gift", param="watch")
    rel = next(r for r in c.state.relationships if r.npc_id == npc_id)
    watch = next(g for g in relationships.GIFTS if g["id"] == "watch")
    assert c.state.money == 10_000 - watch["price"]
    assert rel.relationship == 50 + watch["rel_boost"]


def test_snapshot_exposes_catalogues_for_ui_pickers():
    """The UI gift/money pickers read gift_catalogue and
    money_gift_tiers off the snapshot. Don't strand the pickers."""
    c = GameController()
    c.new_game(seed=1, name="", gender="Female", country="US", talent="Sports")
    snap = c.snapshot()
    assert isinstance(snap.get("gift_catalogue"), list) and len(snap["gift_catalogue"]) >= 5
    assert isinstance(snap.get("money_gift_tiers"), list) and len(snap["money_gift_tiers"]) >= 3
    # Each row should have the fields the UI consumes.
    for g in snap["gift_catalogue"]:
        assert "id" in g and "name" in g and "price" in g and "blurb" in g
    for t in snap["money_gift_tiers"]:
        assert "id" in t and "amount" in t and "blurb" in t


def test_interactions_tuple_lists_every_supported_verb():
    s = _new(money=10_000)
    npc_id = _add_friend(s, rel=80)
    for action in relationships.INTERACTIONS:
        # Picker verbs need a param to succeed but should still RETURN
        # an ActionResult (the refusal message), not raise.
        result = relationships.interact(s, npc_id, action, rng=Rng(1).fork(7))
        assert hasattr(result, "ok")
        assert hasattr(result, "message")
