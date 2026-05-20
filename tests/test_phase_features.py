"""Smoke tests for the new agents / predicates / persistence work."""
from __future__ import annotations

import json
from pathlib import Path

from core import agents, sim
from core.content import countries as countries_mod
from core.content import names as names_mod
from core.predicates import (
    HasJob,
    HasLivingRelationship,
    MinSmarts,
    NoJob,
    evaluate,
)
from core.state import GameState, Job


def _new(seed: int = 1, country: str = "US", gender: str = "Male") -> GameState:
    return sim.new_game(seed=seed, name="", gender=gender, country=country, talent="Sports")


def test_new_game_assigns_country_specific_names_and_city():
    state = _new(country="JP")
    assert state.character.first_name, "first name should be populated"
    assert state.character.last_name, "last name should be populated"
    assert state.character.city in countries_mod.resolve("JP").cities


def test_names_module_returns_pool_for_real_country():
    pool = names_mod.forenames_for("FR", "Female")
    assert pool, "France should have at least some female forenames"


def test_agents_seeded_with_family():
    state = _new()
    assert any(a.role == "Mother" for a in state.agents)
    assert any(a.role == "Father" for a in state.agents)


def test_agent_tick_world_ages_npcs():
    state = _new()
    mum_before = next(a for a in state.agents if a.role == "Mother")
    age_before = mum_before.age
    for _ in range(5):
        sim.age_up(state)
        if state.pending_event_id is not None:
            sim.resolve_choice(state, 0)
    mum_after = next(a for a in state.agents if a.role == "Mother")
    assert mum_after.age >= age_before + 5


def test_predicates_evaluate_empty():
    state = _new()
    assert evaluate(None, state) is True
    assert evaluate([], state) is True


def test_predicate_has_job_versus_no_job():
    state = _new()
    state.career = None
    assert NoJob()(state)
    assert not HasJob()(state)
    state.career = Job("dev", "Dev", 50_000)
    assert HasJob()(state)
    assert not NoJob()(state)


def test_predicate_min_smarts():
    state = _new()
    state.stats.smarts = 70
    assert MinSmarts(60)(state)
    assert not MinSmarts(80)(state)


def test_predicate_living_relationship():
    state = _new()
    assert HasLivingRelationship("Mother")(state)
    for r in state.relationships:
        r.alive = False
    assert not HasLivingRelationship("Mother")(state)


def test_save_load_roundtrip(tmp_path: Path):
    state = _new()
    for _ in range(8):
        sim.age_up(state)
        if state.pending_event_id is not None:
            sim.resolve_choice(state, 0)
    snap = state.to_dict()
    f = tmp_path / "save.json"
    f.write_text(json.dumps(snap))

    loaded = GameState.from_dict(json.loads(f.read_text()))
    assert loaded.character is not None
    assert loaded.character.first_name == state.character.first_name
    assert loaded.character.last_name == state.character.last_name
    assert loaded.character.city == state.character.city
    assert loaded.character.age == state.character.age
    assert len(loaded.agents) == len(state.agents)
    assert len(loaded.feed) == len(state.feed)
