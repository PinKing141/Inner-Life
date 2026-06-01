"""Crime v1 — attempt, arrest, sentence, prison tick, release, record.

Covers: catalogue refusal modes (unknown id, incarcerated, under-age),
success+caught determinism, payout range, stat-bonus shape, arrest
cascade (career/education clear), sim-tick prison override, event
restriction during incarceration, release transition, persistent
record, save/load round-trip, heir-transition reset, controller verbs,
activity refusal while inside.
"""
from __future__ import annotations

import pytest

from controller.game_controller import GameController
from core import crime, events as event_engine, genealogy, sim
from core.content.events import EVENTS
from core.predicates import HasCriminalRecord, IsIncarcerated
from core.rng import Rng
from core.state import CriminalRecord, GameState, Job, Relationship


def _new(seed: int = 1, age: int = 25) -> GameState:
    s = sim.new_game(seed=seed, name="", gender="Female", country="US", talent="Sports")
    s.character.age = age
    return s


def _force_success_seed() -> int:
    """Find a seed where pickpocket succeeds (used to assert success paths
    without flakiness across random changes)."""
    for seed in range(100):
        s = _new(seed=seed)
        result = crime.attempt_crime(s, "pickpocket", Rng(seed + 7777).fork(11))
        if result["ok"] and not result["caught"]:
            return seed + 7777
    pytest.fail("no seed in [0,100) produced a pickpocket success")


def _force_caught_seed() -> int:
    for seed in range(100):
        s = _new(seed=seed)
        # Use bank_heist (18% base) for reliably-caught outcomes.
        result = crime.attempt_crime(s, "bank_heist", Rng(seed + 5555).fork(11))
        if result["ok"] and result["caught"]:
            return seed + 5555
    pytest.fail("no seed in [0,100) produced a bank heist arrest")


# --- Catalogue & refusal modes ------------------------------------------


def test_catalogue_exposes_minimum_metadata():
    """Every entry must have the fields the engine + UI consume."""
    for crime_id, c in crime.CRIME_CATALOGUE.items():
        for key in ("name", "min_age", "base_success", "payout_min",
                    "payout_max", "sentence_years", "stat_modifier", "blurb"):
            assert key in c, f"{crime_id} missing {key}"
        assert c["payout_min"] <= c["payout_max"]
        assert 0 <= c["base_success"] <= 1
        assert c["sentence_years"] >= 1


def test_list_crimes_for_ui_marks_availability():
    s = _new(age=10)  # below pickpocket min_age (12)
    rows = crime.list_crimes_for_ui(s)
    pp = next(r for r in rows if r["id"] == "pickpocket")
    assert pp["available"] is False


def test_unknown_crime_refuses_without_mutating_money():
    s = _new()
    before = s.money
    result = crime.attempt_crime(s, "skynet_takeover", Rng(1).fork(7))
    assert result["ok"] is False
    assert result["refused"] is True
    assert s.money == before
    assert s.crime.is_incarcerated is False


def test_already_incarcerated_refuses_new_crime():
    s = _new()
    s.crime.is_incarcerated = True
    s.crime.sentence_years = 3
    before = s.money
    result = crime.attempt_crime(s, "shoplift", Rng(2).fork(7))
    assert result["ok"] is False
    assert result["refused"] is True
    assert s.money == before


def test_under_age_refuses_serious_crime():
    s = _new(age=14)  # bank_heist min_age 21
    result = crime.attempt_crime(s, "bank_heist", Rng(3).fork(7))
    assert result["ok"] is False
    assert result["refused"] is True
    assert s.crime.is_incarcerated is False


# --- Success path -------------------------------------------------------


def test_clean_getaway_pays_in_range_and_writes_feed():
    seed = _force_success_seed()
    s = _new()
    s.money = 0
    before_happy = s.stats.happiness
    result = crime.attempt_crime(s, "pickpocket", Rng(seed).fork(11))
    assert result["ok"] is True
    assert result["caught"] is False
    payout = result["payout"]
    assert crime.CRIME_CATALOGUE["pickpocket"]["payout_min"] <= payout
    assert payout <= crime.CRIME_CATALOGUE["pickpocket"]["payout_max"]
    assert s.money == payout
    # Happiness gets a small bump on success.
    assert s.stats.happiness >= before_happy
    assert any(e.entry_id.startswith("feed:crime_success:") for e in s.feed)
    assert s.pending_crime_outcome is not None


def test_success_does_not_register_a_conviction():
    seed = _force_success_seed()
    s = _new()
    crime.attempt_crime(s, "pickpocket", Rng(seed).fork(11))
    assert s.crime.is_incarcerated is False
    assert s.crime.past_offences == []


def test_determinism_same_seed_same_outcome():
    seed = 4242
    s1 = _new()
    s2 = _new()
    r1 = crime.attempt_crime(s1, "burglary", Rng(seed).fork(11))
    r2 = crime.attempt_crime(s2, "burglary", Rng(seed).fork(11))
    assert r1["caught"] == r2["caught"]
    assert r1["payout"] == r2["payout"]


# --- Arrest cascade -----------------------------------------------------


def test_caught_locks_player_up_and_drops_career_education_dating():
    seed = _force_caught_seed()
    s = _new()
    s.career = Job(job_id="dev", title="Dev", salary=50_000)
    s.education.in_school = True
    s.dating = {"npc_id": 901, "name": "X", "age": 22, "gender": "Male",
                "chemistry": 30, "dates_been_on": 0, "started_tick": 0}
    result = crime.attempt_crime(s, "bank_heist", Rng(seed).fork(11))
    assert result["caught"] is True
    assert s.crime.is_incarcerated is True
    assert s.crime.sentence_years == crime.CRIME_CATALOGUE["bank_heist"]["sentence_years"]
    assert s.crime.years_served == 0
    assert "Bank Heist" in s.crime.past_offences
    assert s.career is None
    assert s.education.in_school is False
    assert s.dating is None


def test_caught_writes_bad_feed_entry_and_modal_payload():
    seed = _force_caught_seed()
    s = _new()
    crime.attempt_crime(s, "bank_heist", Rng(seed).fork(11))
    assert s.pending_crime_outcome is not None
    assert s.pending_crime_outcome["caught"] is True
    assert any(e.kind == "bad" and e.entry_id.startswith("feed:crime_caught:")
               for e in s.feed)


# --- Predicates ---------------------------------------------------------


def test_is_incarcerated_predicate():
    s = _new()
    assert IsIncarcerated()(s) is False
    s.crime.is_incarcerated = True
    assert IsIncarcerated()(s) is True


def test_has_criminal_record_predicate_survives_release():
    s = _new()
    assert HasCriminalRecord()(s) is False
    s.crime.past_offences.append("Shoplifting")
    # Even with is_incarcerated=False (already released).
    assert HasCriminalRecord()(s) is True


# --- Prison tick + release ----------------------------------------------


def test_prison_tick_advances_counter_and_drifts_stats():
    s = _new()
    s.crime.is_incarcerated = True
    s.crime.sentence_years = 3
    before_smarts = s.stats.smarts
    msg = crime.prison_tick(s)
    assert s.crime.years_served == 1
    assert s.crime.is_incarcerated is True  # not yet released
    assert msg is not None
    # Smarts goes UP one (prison education programs); health drifts down.
    assert s.stats.smarts == before_smarts + 1
    assert any(e.entry_id.startswith("feed:prison:") for e in s.feed)


def test_prison_tick_releases_on_final_year():
    s = _new()
    s.crime.is_incarcerated = True
    s.crime.sentence_years = 2
    s.crime.years_served = 1
    crime.prison_tick(s)
    assert s.crime.is_incarcerated is False
    assert s.crime.years_served == 0
    assert s.crime.sentence_years == 0
    # past_offences UNCHANGED — record survives release.


def test_age_up_routes_through_prison_tick_when_incarcerated():
    """End-to-end: incarcerate, age_up, and confirm the standard career/
    economy ticks were skipped (no salary, no education progression)."""
    s = _new()
    s.crime.is_incarcerated = True
    s.crime.sentence_years = 5
    s.career = None  # already cleared at arrest in real flow
    s.education.in_school = False
    money_before = s.money
    sim.age_up(s)
    assert s.crime.years_served == 1
    # Money unchanged — no salary tick, no economy tick.
    assert s.money == money_before


# --- Event engine filtering ---------------------------------------------


def test_event_roll_restricted_to_prison_events_when_incarcerated():
    """The 100+ free-world events must not fire while the player is in
    prison. Only events with IsIncarcerated() can be rolled."""
    s = _new()
    s.crime.is_incarcerated = True
    s.crime.sentence_years = 10
    s.crime.years_served = 1
    # Force many rolls; every chosen event must be prison-gated.
    sampled = 0
    for seed in range(60):
        chosen = event_engine.roll_event(s, Rng(seed).fork(13))
        if chosen is None:
            continue
        sampled += 1
        preds = chosen.get("predicates") or []
        assert any(p.__class__.__name__ == "IsIncarcerated" for p in preds), (
            f"event {chosen['id']} fired in prison but isn't prison-gated"
        )
    assert sampled > 0, "no prison events fired across 60 rolls"


def test_event_roll_uses_full_catalogue_when_not_incarcerated():
    s = _new()
    # Confirm something gets rolled across enough seeds (sanity, not strict).
    fired_ids = set()
    for seed in range(30):
        chosen = event_engine.roll_event(s, Rng(seed + 100).fork(13))
        if chosen is not None:
            fired_ids.add(chosen["id"])
    assert fired_ids, "no events fired at all in 30 rolls — engine broken?"


# --- Persistence --------------------------------------------------------


def test_criminal_record_roundtrips_through_save_load():
    s = _new()
    s.crime = CriminalRecord(
        is_incarcerated=True, sentence_years=4, years_served=2,
        past_offences=["Burglary", "Shoplifting"],
    )
    s.pending_crime_outcome = {"caught": True, "title": "X", "text": "Y"}
    rebuilt = GameState.from_dict(s.to_dict())
    assert rebuilt.crime.is_incarcerated is True
    assert rebuilt.crime.sentence_years == 4
    assert rebuilt.crime.years_served == 2
    assert rebuilt.crime.past_offences == ["Burglary", "Shoplifting"]
    assert rebuilt.pending_crime_outcome == s.pending_crime_outcome


# --- Heir transition reset ----------------------------------------------


def test_continue_as_heir_clears_crime_state():
    """A new generation never inherits the deceased's record."""
    from core.agents import Agent
    s = _new(seed=42)
    s.relationships.append(Relationship(
        npc_id=900, name="P", kind="Partner", relationship=80, alive=True,
    ))
    s.agents.append(Agent(
        npc_id=900, first_name="P", last_name="X", gender="NonBinary",
        role="Partner", age=30, country=s.character.country, city="",
    ))
    genealogy.begin_pregnancy(s)
    s.tick += 1
    # Force a healthy birth so there's a child to continue as.
    for seed in range(20):
        s_try = _new(seed=42)
        s_try.relationships.append(Relationship(
            npc_id=900, name="P", kind="Partner", relationship=80, alive=True,
        ))
        s_try.agents.append(Agent(
            npc_id=900, first_name="P", last_name="X", gender="NonBinary",
            role="Partner", age=30, country=s_try.character.country, city="",
        ))
        genealogy.begin_pregnancy(s_try)
        s_try.tick += 1
        if genealogy.resolve_pregnancy(s_try, Rng(seed).fork(7)) is not None:
            s = s_try
            break
    heir_id = s.character.children[0]
    s.crime.is_incarcerated = True
    s.crime.sentence_years = 10
    s.crime.past_offences = ["Bank Heist"]
    s.pending_crime_outcome = {"caught": True}
    s.mode = "DEATH"
    genealogy.continue_as_heir(s, heir_id)
    assert s.crime.is_incarcerated is False
    assert s.crime.past_offences == []
    assert s.pending_crime_outcome is None


# --- Controller verbs ---------------------------------------------------


def test_controller_commit_crime_writes_to_feed_and_pending():
    c = GameController()
    c.new_game(seed=1, name="", gender="Male", country="US", talent="Sports")
    c.state.character.age = 25
    snap = c.commit_crime("shoplift")
    assert snap["pending_crime_outcome"] is not None
    assert any("Shoplift" in e["text"] or "walked away" in e["text"]
               or "caught" in e["text"].lower()
               for e in snap["feed"])


def test_controller_acknowledge_crime_outcome_clears_modal():
    c = GameController()
    c.new_game(seed=2, name="", gender="Female", country="US", talent="Sports")
    c.state.character.age = 25
    c.state.pending_crime_outcome = {"caught": False, "title": "T", "text": "U"}
    snap = c.acknowledge_crime_outcome()
    assert snap["pending_crime_outcome"] is None


def test_controller_activity_refuses_while_incarcerated():
    """Tapping 'gym' from a cell must refuse with a visible feed line —
    not silently apply the stat bump."""
    c = GameController()
    c.new_game(seed=3, name="", gender="Male", country="US", talent="Sports")
    c.state.character.age = 25
    c.state.money = 10_000
    c.state.crime.is_incarcerated = True
    c.state.crime.sentence_years = 3
    before_health = c.state.stats.health
    snap = c.activity("gym")
    assert c.state.stats.health == before_health
    # And the player gets feedback — last feed entry says so.
    assert "prison" in snap["feed"][-1]["text"].lower()


def test_snapshot_exposes_crimes_for_ui():
    c = GameController()
    c.new_game(seed=4, name="", gender="Male", country="US", talent="Sports")
    c.state.character.age = 25
    snap = c.snapshot()
    assert "crimes" in snap
    assert any(row["id"] == "shoplift" for row in snap["crimes"])
