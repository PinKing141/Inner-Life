"""Love/Dating v1 — player-driven romance loop.

Verifies the state machine (single → dating → partnered → single via
break-up), refusal modes (age, already partnered, can't afford a date,
chemistry too low to commit), determinism via the seeded RNG, the
sim-tick guard that stops tick_partner from displacing the player's
prospect, and save/load round-trip of state.dating.
"""
from __future__ import annotations

import pytest

from controller.game_controller import GameController
from core import agents, dating, sim
from core.predicates import IsDating, IsSingle, MinChemistry
from core.rng import Rng
from core.state import GameState, Relationship


def _new(seed: int = 1, age: int = 22) -> GameState:
    s = sim.new_game(seed=seed, name="", gender="Female", country="US", talent="Sports")
    s.character.age = age
    return s


# --- ask_someone_out ------------------------------------------------------


def test_ask_someone_out_creates_prospect_and_relationship():
    s = _new()
    ok, msg = dating.ask_someone_out(s, Rng(1).fork(7))
    assert ok is True
    assert s.dating is not None
    npc_id = s.dating["npc_id"]
    # Agent and Relationship both exist; both use role/kind = "Dating".
    agent = next(a for a in s.agents if a.npc_id == npc_id)
    rel = next(r for r in s.relationships if r.npc_id == npc_id)
    assert agent.role == "Dating"
    assert rel.kind == "Dating"
    assert rel.alive is True
    # Chemistry starts in the spark range — never high enough to commit yet.
    assert s.dating["chemistry"] < dating.COMMIT_CHEMISTRY_THRESHOLD


def test_ask_someone_out_refuses_under_age():
    s = _new(age=15)
    ok, msg = dating.ask_someone_out(s, Rng(2).fork(7))
    assert ok is False
    assert s.dating is None


def test_ask_someone_out_refuses_when_already_dating():
    s = _new()
    dating.ask_someone_out(s, Rng(3).fork(7))
    ok, _ = dating.ask_someone_out(s, Rng(4).fork(7))
    assert ok is False  # Must not silently overwrite the existing arc.


def test_ask_someone_out_refuses_when_already_partnered():
    s = _new()
    s.relationships.append(Relationship(
        npc_id=900, name="Spouse", kind="Partner", relationship=80, alive=True,
    ))
    ok, msg = dating.ask_someone_out(s, Rng(5).fork(7))
    assert ok is False
    assert "committed" in msg.lower() or "already" in msg.lower()


def test_ask_someone_out_is_deterministic_under_same_rng():
    """Same seed + same player state -> same prospect name + chemistry.
    Determinism is the contract."""
    s1 = _new(seed=42)
    s2 = _new(seed=42)
    dating.ask_someone_out(s1, Rng(99).fork(7))
    dating.ask_someone_out(s2, Rng(99).fork(7))
    assert s1.dating == s2.dating


# --- go_on_date -----------------------------------------------------------


def test_go_on_date_raises_chemistry_and_charges_money():
    s = _new()
    s.money = 1_000
    dating.ask_someone_out(s, Rng(11).fork(7))
    before = s.dating["chemistry"]
    money_before = s.money
    ok, _ = dating.go_on_date(s, Rng(12).fork(7))
    assert ok is True
    assert s.dating["chemistry"] > before
    assert s.money == money_before - dating.DATE_COST
    assert s.dating["dates_been_on"] == 1


def test_go_on_date_refuses_without_a_prospect():
    s = _new()
    s.money = 1_000
    ok, msg = dating.go_on_date(s, Rng(13).fork(7))
    assert ok is False


def test_go_on_date_refuses_when_broke():
    s = _new()
    dating.ask_someone_out(s, Rng(14).fork(7))
    s.money = dating.DATE_COST - 1
    ok, _ = dating.go_on_date(s, Rng(15).fork(7))
    assert ok is False


def test_go_on_date_caps_chemistry_at_100():
    """Repeated dates with high-looks player must not push past 100."""
    s = _new()
    s.money = 100_000
    s.stats.looks = 100
    dating.ask_someone_out(s, Rng(21).fork(7))
    for i in range(50):
        dating.go_on_date(s, Rng(100 + i).fork(7))
    assert s.dating["chemistry"] == 100


# --- become_official ------------------------------------------------------


def test_become_official_refuses_under_chemistry_threshold():
    s = _new()
    dating.ask_someone_out(s, Rng(31).fork(7))
    s.dating["chemistry"] = dating.COMMIT_CHEMISTRY_THRESHOLD - 1
    ok, msg = dating.become_official(s)
    assert ok is False
    assert "chemistry" in msg.lower()


def test_become_official_promotes_dating_to_partner():
    s = _new()
    dating.ask_someone_out(s, Rng(41).fork(7))
    npc_id = s.dating["npc_id"]
    s.dating["chemistry"] = 80
    ok, msg = dating.become_official(s)
    assert ok is True
    assert s.dating is None  # cleared
    rel = next(r for r in s.relationships if r.npc_id == npc_id)
    agent = next(a for a in s.agents if a.npc_id == npc_id)
    assert rel.kind == "Partner"
    assert agent.role == "Partner"
    assert agent.marital_status == "Partnered"
    assert rel.relationship >= 75  # floor on commitment


def test_become_official_refuses_without_a_prospect():
    s = _new()
    ok, _ = dating.become_official(s)
    assert ok is False


# --- break_up -------------------------------------------------------------


def test_break_up_ends_dating_arc():
    s = _new()
    dating.ask_someone_out(s, Rng(51).fork(7))
    npc_id = s.dating["npc_id"]
    ok, msg = dating.break_up(s)
    assert ok is True
    assert s.dating is None
    # Relationship gone, agent stays in the world (re-labeled "Ex").
    assert not any(r.npc_id == npc_id for r in s.relationships)
    ex = next(a for a in s.agents if a.npc_id == npc_id)
    assert ex.role == "Ex"


def test_break_up_ends_partnership_takes_priority_over_dating_when_both():
    """Defensive: state.dating shouldn't coexist with a Partner (verbs
    enforce that), but if a bug let it happen, Partner ends first
    because that's the bigger commitment to dissolve."""
    s = _new()
    s.relationships.append(Relationship(
        npc_id=900, name="Spouse", kind="Partner", relationship=80, alive=True,
    ))
    s.dating = {"npc_id": 901, "name": "Side", "age": 22, "gender": "Male",
                "chemistry": 30, "dates_been_on": 0, "started_tick": 0}
    ok, msg = dating.break_up(s)
    assert ok is True
    assert "Spouse" in msg
    assert not any(r.kind == "Partner" for r in s.relationships)
    # The dating arc is left for a subsequent break_up call.
    assert s.dating is not None


def test_break_up_refuses_when_single():
    s = _new()
    ok, _ = dating.break_up(s)
    assert ok is False


# --- Predicates -----------------------------------------------------------


def test_predicates_track_state_transitions():
    s = _new()
    assert IsSingle()(s) is True
    assert IsDating()(s) is False
    dating.ask_someone_out(s, Rng(61).fork(7))
    assert IsSingle()(s) is False
    assert IsDating()(s) is True
    s.dating["chemistry"] = 80
    dating.become_official(s)
    assert IsSingle()(s) is False  # partnered
    assert IsDating()(s) is False


def test_min_chemistry_predicate_is_false_when_not_dating():
    s = _new()
    assert MinChemistry(50)(s) is False  # not dating at all
    dating.ask_someone_out(s, Rng(71).fork(7))
    s.dating["chemistry"] = 60
    assert MinChemistry(50)(s) is True
    assert MinChemistry(70)(s) is False


# --- Sim integration ------------------------------------------------------


def test_tick_partner_defers_to_active_dating_arc():
    """While the player is mid-arc, the random partner pathway must not
    steal in and mint a surprise Partner that displaces the prospect."""
    s = _new()
    dating.ask_someone_out(s, Rng(81).fork(7))
    npc_id_before = s.dating["npc_id"]
    for i in range(50):
        agents.tick_partner(s, Rng(1000 + i).fork(31))
    # Still dating the same person, no Partner introduced.
    assert s.dating is not None
    assert s.dating["npc_id"] == npc_id_before
    assert not any(r.kind == "Partner" for r in s.relationships)


# --- Save / load ---------------------------------------------------------


def test_dating_state_survives_save_load_roundtrip():
    s = _new()
    s.money = 500
    dating.ask_someone_out(s, Rng(91).fork(7))
    dating.go_on_date(s, Rng(92).fork(7))
    rebuilt = GameState.from_dict(s.to_dict())
    assert rebuilt.dating == s.dating


# --- Controller verbs ---------------------------------------------------


def test_controller_dating_verbs_write_to_feed():
    c = GameController()
    c.new_game(seed=7, name="", gender="Male", country="US", talent="Sports")
    c.state.character.age = 22
    c.state.money = 500
    snap = c.ask_someone_out()
    assert snap["dating"] is not None
    feed_text = " ".join(e["text"] for e in snap["feed"])
    assert "asked" in feed_text.lower()
    c.go_on_date()
    c.state.dating["chemistry"] = 80  # force commit threshold
    snap = c.become_official()
    assert snap["dating"] is None
    assert any(r["kind"] == "Partner" for r in snap["relationships"])


def test_controller_break_up_after_partnership():
    """End-to-end: ask out → date → commit → break up. The Partner
    must be gone from relationships and the player back to IsSingle."""
    c = GameController()
    c.new_game(seed=8, name="", gender="Female", country="US", talent="Sports")
    c.state.character.age = 25
    c.state.money = 1_000
    c.ask_someone_out()
    c.state.dating["chemistry"] = 80
    c.become_official()
    assert any(r["kind"] == "Partner" for r in c.snapshot()["relationships"])
    snap = c.break_up()
    assert not any(r["kind"] == "Partner" for r in snap["relationships"])
    assert IsSingle()(c.state) is True
