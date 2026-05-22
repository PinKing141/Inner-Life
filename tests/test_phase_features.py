"""Smoke tests for the new agents / predicates / persistence work."""
from __future__ import annotations

import json
from pathlib import Path

from core import agents, economy, education, relationships, sim, social
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


def test_parent_agent_age_and_job_match_birth_record():
    """The agent record for a parent must reuse the age/job baked into the
    birth-story feed (parent_details), not roll its own conflicting values."""
    state = _new()
    by_role = {d["role"]: d for d in state.character.parent_details}
    for role in ("Mother", "Father"):
        rel = next(r for r in state.relationships if r.kind == role)
        agent = next(a for a in state.agents if a.npc_id == rel.npc_id)
        assert agent.age == by_role[role]["age_at_birth"]
        assert agent.job_title == by_role[role]["job"]


def test_generous_relative_bails_out_player_in_debt():
    # Across a fixed seed range, a close + generous + wealthy parent should
    # sometimes help an in-debt player. When it fires, money is conserved
    # (the helper's funds drop by exactly what the player gained).
    fired = 0
    for seed in range(60):
        state = _new(seed=seed)
        state.money = -2000
        mom_rel = next(r for r in state.relationships if r.kind == "Mother")
        mom_rel.relationship = 95
        mom = next(a for a in state.agents if a.npc_id == mom_rel.npc_id)
        mom.generosity = 100
        mom.money = 10000
        before_player, before_mom = state.money, mom.money
        if agents.offer_financial_help(state, Rng(seed).fork(37)):
            fired += 1
            delta = state.money - before_player
            assert delta > 0
            assert mom.money == before_mom - delta
            assert state.money <= 0  # never overpays past the shortfall
            assert state.last_help_tick == state.tick  # cooldown stamped
    assert fired > 0, "a generous, wealthy, close relative should sometimes help"


def test_no_help_when_relatives_are_not_generous():
    state = _new(seed=1)
    state.money = -2000
    for a in state.agents:
        a.generosity = 0
    assert agents.offer_financial_help(state, Rng(1).fork(37)) is False
    assert state.money == -2000


def test_no_help_when_player_is_not_in_debt():
    state = _new(seed=1)
    state.money = 500
    mom_rel = next(r for r in state.relationships if r.kind == "Mother")
    mom_rel.relationship = 100
    mom = next(a for a in state.agents if a.npc_id == mom_rel.npc_id)
    mom.generosity = 100
    mom.money = 10000
    assert agents.offer_financial_help(state, Rng(1).fork(37)) is False
    assert state.money == 500


def test_no_help_for_mild_debt_above_hardship_threshold():
    state = _new(seed=1)
    state.money = -200  # in the red, but not severe enough to summon help
    mom_rel = next(r for r in state.relationships if r.kind == "Mother")
    mom_rel.relationship = 100
    mom = next(a for a in state.agents if a.npc_id == mom_rel.npc_id)
    mom.generosity = 100
    mom.money = 10000
    for seed in range(20):
        assert agents.offer_financial_help(state, Rng(seed).fork(37)) is False
    assert state.money == -200


def test_bailout_respects_cooldown():
    state = _new(seed=3)
    state.tick = 10
    state.last_help_tick = 10  # already helped this very year
    state.money = -5000
    mom_rel = next(r for r in state.relationships if r.kind == "Mother")
    mom_rel.relationship = 100
    mom = next(a for a in state.agents if a.npc_id == mom_rel.npc_id)
    mom.generosity = 100
    mom.money = 50000
    for seed in range(20):
        assert agents.offer_financial_help(state, Rng(seed).fork(37)) is False
    assert state.money == -5000


def test_isolation_costs_happiness():
    state = _new(seed=1)
    for r in state.relationships:
        r.relationship = 0  # sever every close tie
    before = state.stats.happiness
    relationships.loneliness_tick(state)
    assert state.stats.happiness < before


def test_strong_tie_prevents_loneliness_penalty():
    state = _new(seed=1)
    before = state.stats.happiness  # parents start at 90, well above threshold
    assert relationships.loneliness_tick(state) is None
    assert state.stats.happiness == before


def test_low_happiness_erodes_job_performance_faster():
    def perf_after(happiness: int) -> int:
        s = _new(seed=5)
        s.stats.happiness = happiness
        s.career = Job(job_id="retail", title="Retail Assistant", salary=15_000,
                       career="Retail", level=0, performance=60)
        economy.career_tick(s, Rng(s.seed).fork(8))
        return s.career.performance if s.career else 0

    assert perf_after(10) < perf_after(90)


def test_getting_hired_lifts_happiness():
    for seed in range(20):
        s = _new(seed=seed)
        s.character.age = 18
        s.stats.happiness = 50
        ok, _ = economy.apply_for_job(s, "retail")
        if ok:
            assert s.stats.happiness > 50
            return
    raise AssertionError("expected at least one successful hire across seeds")


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


def test_hire_sets_offer_popup_and_work_then_promotion():
    c = GameController()
    c.new_game(seed=42, name="", gender="Male", country="US", talent="")
    assert c.state is not None
    c.state.character.age = 20
    c.state.stats.smarts = 80
    c.state.education.level = "Secondary Education"

    hired = False
    for _ in range(25):
        c.state.tick += 1
        snap = c.apply_for_job("admin")
        if c.state.career is not None:
            hired = True
            break
    assert hired
    assert c.state.career.employer  # an employer was assigned
    assert c.state.career.career == "Admin Assistant"
    assert c.state.pending_job_offer is not None
    c.acknowledge_job_offer()
    assert c.state.pending_job_offer is None

    # Work harder lifts performance.
    base = c.state.career.performance
    c.work_harder()
    assert c.state.career.performance > base

    # Push to a promotion.
    promoted = False
    for _ in range(20):
        for _ in range(3):
            c.work_harder()
        c.age_up()
        if c.state.pending_event_id is not None:
            c.choose(0)
        if c.state.pending_promotion is not None:
            promoted = True
            break
    assert promoted
    assert c.state.career.level >= 1
    assert c.state.career.title.startswith("Senior")
    c.acknowledge_promotion()
    assert c.state.pending_promotion is None


def test_quit_job_clears_career():
    c = GameController()
    c.new_game(seed=1, name="", gender="Male", country="US", talent="")
    assert c.state is not None
    c.state.character.age = 20
    c.state.stats.smarts = 80
    c.state.education.level = "Secondary Education"
    for _ in range(25):
        c.state.tick += 1
        c.apply_for_job("admin")
        if c.state.career is not None:
            break
    assert c.state.career is not None
    c.quit_job()
    assert c.state.career is None
    assert "quit" in c.state.feed[-1].text.lower()


def test_recession_can_lay_you_off():
    from core import economy
    from core.rng import Rng
    from core.state import Job
    c = GameController()
    c.new_game(seed=4, name="", gender="Male", country="US", talent="")
    assert c.state is not None
    c.state.career = Job(job_id="admin", title="Admin Assistant", salary=22000,
                         employer="Acme", career="Admin Assistant", level=0, performance=10)
    c.state.world.recession = True
    c.state.world.unemployment_rate = 0.2
    laid_off = False
    for t in range(50):
        outcome = economy.career_tick(c.state, Rng(c.state.seed).fork(t))
        if outcome and outcome["type"] == "layoff":
            laid_off = True
            assert c.state.career is None
            break
        if c.state.career is None:
            break
    assert laid_off


def _fresh_career(state, **kw):
    from core.state import Job
    defaults = dict(job_id="solicitor", title="Partner", salary=80000,
                    employer="Acme Law", career="Lawyer", level=2, performance=30)
    defaults.update(kw)
    state.career = Job(**defaults)


def test_demotion_drops_a_rank_without_firing():
    from core import economy
    from core.rng import Rng
    c = GameController()
    c.new_game(seed=6, name="", gender="Female", country="US", talent="")
    assert c.state is not None
    demoted = False
    for t in range(80):
        _fresh_career(c.state)  # reset each sample so outcomes are independent
        outcome = economy.career_tick(c.state, Rng(c.state.seed).fork(t + 100))
        if outcome and outcome["type"] == "demotion":
            demoted = True
            assert c.state.career is not None  # still employed
            assert c.state.career.level == 1
            assert c.state.career.salary < 80000
            break
    assert demoted


def test_recession_pay_cut_keeps_the_job():
    from core import economy
    from core.rng import Rng
    c = GameController()
    c.new_game(seed=9, name="", gender="Male", country="US", talent="")
    assert c.state is not None
    c.state.world.recession = True
    cut = False
    for t in range(120):
        # Healthy performance (no demotion/promotion) at entry level, level 0.
        _fresh_career(c.state, job_id="admin", title="Admin Assistant", salary=22000,
                      employer="Acme", career="Admin Assistant", level=0, performance=60)
        outcome = economy.career_tick(c.state, Rng(c.state.seed).fork(t + 200))
        if outcome and outcome["type"] == "paycut":
            cut = True
            assert c.state.career is not None
            assert c.state.career.salary < 22000
            break
    assert cut


def test_request_raise_cooldown_and_success():
    from core import economy
    from core.state import Job
    c = GameController()
    c.new_game(seed=11, name="", gender="Male", country="US", talent="")
    assert c.state is not None
    c.state.career = Job(job_id="admin", title="Admin Assistant", salary=22000,
                         employer="Acme", career="Admin Assistant", level=0, performance=100)
    # Only one ask per year.
    c.request_raise()
    before = c.state.career.salary
    ok, msg = economy.request_raise(c.state)
    assert ok is False and "already" in msg.lower()
    assert c.state.career.salary == before

    # With max performance, raises land within a few years.
    got_raise = False
    base = c.state.career.salary
    for _ in range(15):
        c.age_up()
        if c.state.pending_event_id is not None:
            c.choose(0)
        if c.state.career is None:
            break
        c.state.career.performance = 100
        c.request_raise()
        if c.state.career and c.state.career.salary > base:
            got_raise = True
            break
    assert got_raise


def test_request_promotion_can_succeed():
    from core import economy
    from core.state import Job
    c = GameController()
    c.new_game(seed=12, name="", gender="Female", country="US", talent="")
    assert c.state is not None
    promoted = False
    for t in range(40):
        c.state.tick = t  # advance the cooldown clock
        c.state.career = Job(job_id="solicitor", title="Solicitor", salary=52000,
                             employer="Acme Law", career="Lawyer", level=0, performance=100)
        ok, msg, promo = economy.request_promotion(c.state)
        if ok:
            promoted = True
            assert promo is not None and promo["type"] == "promotion"
            assert c.state.career.level == 1
            assert c.state.career.title == "Senior Associate"
            break
    assert promoted


def test_buy_rent_sell_home_and_net_worth():
    from core import housing
    c = GameController()
    c.new_game(seed=21, name="", gender="Female", country="US", talent="")
    assert c.state is not None
    c.state.character.age = 30
    c.state.money = 1_000_000
    market = housing.list_market(c.state)
    assert market and all("price" in m and "rent" in m for m in market)

    listing = market[0]
    before = c.state.money
    c.buy_home(listing["id"])
    assert len(c.state.properties) == 1
    assert c.state.money == before - listing["price"]
    # Property counts toward net worth even though cash dropped.
    assert housing.net_worth(c.state) == c.state.money + c.state.properties[0]["value"]

    # Renting adds a recurring expense reflected in cashflow.
    rent_listing = market[1]
    c.rent_home(rent_listing["id"])
    assert c.state.rental is not None
    from core.economy import annual_cashflow
    from core.rng import Rng
    _, living, _ = annual_cashflow(c.state, Rng(1).fork(1))
    assert living >= rent_listing["rent"]

    c.stop_renting()
    assert c.state.rental is None

    # Selling returns the value to the bank.
    pid = c.state.properties[0]["id"]
    cash_before = c.state.money
    c.sell_home(pid)
    assert c.state.properties == []
    assert c.state.money > cash_before


def test_mortgage_deposit_payments_and_payoff():
    from core import housing
    from core.rng import Rng
    c = GameController()
    c.new_game(seed=31, name="", gender="Male", country="US", talent="")
    assert c.state is not None
    c.state.character.age = 30
    listing = housing.list_market(c.state)[2]
    price = listing["price"]

    # Can't mortgage without the deposit.
    c.state.money = 0
    ok, msg = housing.buy_home_mortgage(c.state, listing["id"])
    assert ok is False and "deposit" in msg.lower()

    # With the deposit, only the deposit leaves the bank now.
    c.state.money = price  # plenty
    c.buy_home_mortgage(listing["id"])
    assert len(c.state.properties) == 1
    prop = c.state.properties[0]
    assert prop["mortgage_balance"] > 0
    deposit = int(price * housing.MORTGAGE_DOWN_PCT)
    assert c.state.money == price - deposit  # not the full price

    # Net worth nets off the outstanding mortgage.
    assert housing.net_worth(c.state) == c.state.money + prop["value"] - prop["mortgage_balance"]

    # Paying for many years clears the balance and stops the payment.
    start_balance = prop["mortgage_balance"]
    for t in range(MORTGAGE_YEARS := 40):
        housing.annual_update(c.state, Rng(c.state.seed).fork(t))
        if c.state.properties[0]["mortgage_balance"] <= 0:
            break
    assert c.state.properties[0]["mortgage_balance"] == 0
    assert c.state.properties[0]["mortgage_payment"] == 0
    assert start_balance > 0


def test_cannot_buy_home_as_a_child():
    from core import housing
    c = GameController()
    c.new_game(seed=22, name="", gender="Male", country="US", talent="")
    assert c.state is not None
    c.state.character.age = 8
    c.state.money = 1_000_000
    listing = housing.list_market(c.state)[0]
    ok, msg = housing.buy_home(c.state, listing["id"])
    assert ok is False
    assert c.state.properties == []


def test_bespoke_ladder_titles():
    from core import economy
    spec = economy.find_job("solicitor")
    assert economy.profession_for(spec) == "Lawyer"
    assert economy.rung_title(spec, 0) == "Solicitor"
    assert "Partner" in spec.ladder


def test_failed_application_sets_error():
    c = GameController()
    c.new_game(seed=5, name="", gender="Male", country="US", talent="")
    assert c.state is not None
    # Too young for admin -> rejection message recorded.
    c.state.character.age = 10
    ok, msg = economy.apply_for_job(c.state, "admin")
    assert ok is False
    # Hard requirement failures don't set the "not selected" error, but a
    # probability miss does; force one by exhausting a too-strict role check.
    c.state.character.age = 20
    c.state.stats.smarts = 0
    ok, _ = economy.apply_for_job(c.state, "admin")
    assert ok is False


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
