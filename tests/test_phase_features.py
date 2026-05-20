"""Smoke tests for the new agents / predicates / persistence work."""
from __future__ import annotations

import json
from pathlib import Path

from core import agents, sim, social
from core.content import countries as countries_mod
from core.content import names as names_mod
from core.rng import Rng
from core.predicates import (
    HasJob,
    HasLivingRelationship,
    MinSmarts,
    NoJob,
    evaluate,
)
from core.state import GameState, Job
from controller.game_controller import GameController


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


def test_social_graph_seeded_with_allowed_relationship_types():
    state = _new()
    sim.age_up(state)
    if state.pending_event_id is not None:
        sim.resolve_choice(state, 0)
    assert state.social_edges, "social graph should be seeded after the first yearly tick"
    assert all(e.relation_type in ("friend", "family", "enemy", "coworker") for e in state.social_edges)


def test_rumour_propagation_attenuates():
    state = _new()
    social.seed_social_graph(state, Rng(state.seed).fork(999))
    if not state.social_edges:
        return
    first = state.social_edges[0]
    first.contact_rate = 1.0
    first.trust = 100
    state.rumours.append(social.Rumour(
        topic="test_rumour",
        stance="negative",
        origin_id=first.source_id,
        current_id=first.source_id,
        intensity=1.0,
        credibility=0.9,
        ttl=3,
        seen_by=[],
    ))
    social.tick_social(state, Rng(state.seed).fork(1001))
    assert any(r.intensity < 1.0 for r in state.rumours if r.topic == "test_rumour")


def test_university_plan_major_and_dropout_flow():
    c = GameController()
    c.new_game(seed=42, name="", gender="Female", country="US", talent="Sports")
    assert c.state is not None
    c.set_university_plan(attend=True, major="Computer Science")
    assert c.state.education.university_intent == "attend"
    assert c.state.education.university_major == "Computer Science"
    # age to 18 so education tick graduates + enrolls in the same year
    while c.state.character and c.state.character.age < 18:
        c.age_up()
        if c.state.pending_event_id is not None:
            c.choose(0)
    assert c.state.education.level == "University"
    assert c.state.education.in_school is True
    assert "You graduated secondary school." in c.state.feed[-1].text
    assert "You enrolled in Computer Science course at university." in c.state.feed[-1].text
    c.drop_out_university()
    assert c.state.education.university_dropped_out is True
    assert c.state.education.in_school is False


def test_university_skip_plan_is_serialized():
    c = GameController()
    c.new_game(seed=7, name="", gender="Male", country="US", talent="Sports")
    assert c.state is not None
    c.set_university_plan(attend=False)
    snap = c.state.to_dict()
    assert snap["education"]["university_intent"] == "skip"
    assert snap["education"]["university_major"] == ""


def test_secondary_graduation_skip_happens_at_18():
    c = GameController()
    c.new_game(seed=11, name="", gender="Male", country="US", talent="Sports")
    assert c.state is not None
    c.set_university_plan(attend=False)
    while c.state.character and c.state.character.age < 18:
        c.age_up()
        if c.state.pending_event_id is not None:
            c.choose(0)
    assert c.state.education.level == "Secondary Education"
    assert c.state.education.in_school is False
    age_18_entries = [f.text for f in c.state.feed if f.age == 18]
    assert any("You graduated secondary school." in t for t in age_18_entries)
    assert any("You chose not to attend university." in t for t in age_18_entries)
