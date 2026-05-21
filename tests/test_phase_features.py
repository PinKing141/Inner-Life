"""Smoke tests for the new agents / predicates / persistence work."""
from __future__ import annotations

import json
from pathlib import Path

from core import agents, economy, education, sim, social
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


def _age_to(c, target):
    while c.state.character and c.state.character.age < target:
        c.age_up()
        if c.state.pending_event_id is not None:
            c.choose(0)


def _take_exam(c, correct=True):
    while c.state.exam and not c.state.exam.get("finished"):
        i = c.state.exam["index"]
        q = c.state.exam["questions"][i]
        ans = q["answer"] if correct else (q["answer"] + 1) % 3
        c.answer_exam(ans)


def test_final_exam_then_university_popup_and_degree():
    c = GameController()
    c.new_game(seed=99, name="Ada", gender="Female", country="US", talent="Academics")
    assert c.state is not None
    # Secondary graduation triggers the final exam, not the course picker yet.
    _age_to(c, 18)
    edu = c.state.education
    assert edu.awaiting_exam is True
    assert c.state.exam is not None and len(c.state.exam["questions"]) == 10
    assert c.state.exam["questions"][0]["prompt"] == "What is your name?"

    # Ace the exam -> top grade -> admitted with the course picker open.
    _take_exam(c, correct=True)
    edu = c.state.education
    assert edu.exam_taken is True
    assert edu.final_school_grade == "A"
    assert edu.admitted_tier == "Prestigious"
    assert edu.scholarship == "full"
    assert edu.awaiting_university_choice is True

    # Enrol in a science course.
    c.set_university_plan(attend=True, major="Physics")
    edu = c.state.education
    assert edu.in_school is True and edu.level == "University"
    assert edu.degree_field == "science"
    assert edu.university_name

    # Graduate after four years.
    _age_to(c, 22)
    edu = c.state.education
    assert edu.degree_completed is True
    assert edu.degree_award_pending is True
    c.acknowledge_degree()
    assert c.state.education.degree_award_pending is False


def test_tuition_pushes_balance_negative_and_work_repays():
    c = GameController()
    c.new_game(seed=3, name="", gender="Male", country="US", talent="Academics")
    assert c.state is not None
    edu = c.state.education
    edu.admitted_tier = "Standard"
    edu.scholarship = "none"
    c.state.character.age = 18
    education.enroll_program(c.state, "University", major="Physics")

    start = c.state.money
    _age_to(c, 19)
    assert c.state.money < start  # tuition put us into the negatives
    after_one = c.state.money
    _age_to(c, 20)
    assert c.state.money < after_one  # debt deepens each study year

    _age_to(c, 22)
    assert c.state.education.degree_completed is True

    # A salary repays the negative balance over the working years.
    c.state.stats.smarts = 95
    for _ in range(30):
        c.state.tick += 1
        ok, _msg = economy.apply_for_job(c.state, "grocer")
        if ok:
            break
    assert c.state.career is not None
    low = c.state.money
    _age_to(c, c.state.character.age + 12)
    assert c.state.money > low


def test_postgrad_master_then_doctorate():
    c = GameController()
    c.new_game(seed=8, name="", gender="Female", country="US", talent="Academics")
    assert c.state is not None
    edu = c.state.education
    edu.degree_completed = True
    edu.university_major = "Physics"
    edu.degree_field = "science"
    c.state.character.age = 22

    c.enroll_postgrad("Master's Degree")
    assert c.state.education.level == "Master's Degree"
    assert c.state.education.in_school is True
    _age_to(c, 24)
    assert c.state.education.masters_completed is True

    c.acknowledge_degree()
    c.enroll_postgrad("Doctorate")
    assert c.state.education.level == "Doctorate"
    _age_to(c, 27)
    assert c.state.education.doctorate_completed is True


def test_cheating_reveals_answer_or_ends_exam():
    c = GameController()
    c.new_game(seed=2, name="Bo", gender="Male", country="US", talent="Academics")
    assert c.state is not None
    _age_to(c, 18)
    assert c.state.exam is not None
    c.cheat_exam()
    ex = c.state.exam
    if ex.get("caught"):
        assert ex.get("finished") is True
        assert c.state.education.final_school_grade == "F"
    else:
        assert ex.get("revealed") is not None


def test_relationship_interactions_move_the_bar():
    c = GameController()
    c.new_game(seed=42, name="", gender="Male", country="US", talent="")
    assert c.state is not None
    nid = c.state.relationships[0].npc_id
    base = c.state.relationships[0].relationship

    c.relationship_action(nid, "argue")
    after_argue = c.state.relationships[0].relationship
    assert after_argue < base

    c.relationship_action(nid, "compliment")
    assert c.state.relationships[0].relationship > after_argue

    # A gift you can't afford is rejected and changes nothing.
    c.state.money = 0
    before = c.state.relationships[0].relationship
    c.relationship_action(nid, "gift")
    assert c.state.relationships[0].relationship == before
    assert "afford" in c.state.feed[-1].text

    # With cash, the gift lands and costs money.
    c.state.money = 500
    c.relationship_action(nid, "gift")
    assert c.state.money == 450
    assert c.state.relationships[0].relationship > before


def test_degree_field_gates_jobs():
    c = GameController()
    c.new_game(seed=5, name="", gender="Male", country="US", talent="Academics")
    assert c.state is not None
    # Force a completed Fine Art degree and adult age with high smarts.
    edu = c.state.education
    edu.level = "University"
    edu.degree_completed = True
    edu.degree_field = "arts"
    c.state.character.age = 30
    c.state.stats.smarts = 95

    # Scientist needs a science degree -> hard reject for a Fine Art graduate.
    ok, msg = economy.apply_for_job(c.state, "scientist")
    assert ok is False
    assert "require" in msg.lower()

    # A no-degree job should accept (probability is generous; both forks succeed).
    hired = False
    for _ in range(20):
        c.state.tick += 1
        ok, _msg = economy.apply_for_job(c.state, "grocer")
        if ok:
            hired = True
            break
    assert hired is True
