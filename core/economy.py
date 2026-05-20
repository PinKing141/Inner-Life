"""Economy: career, salary, living costs.

The annual budget pass runs from core.sim.tick. This module just declares the
rules for whether a job application succeeds and what the yearly cashflow
looks like.
"""
from __future__ import annotations

from core.content.jobs import JOBS, JobSpec, education_meets
from core.rng import Rng
from core.state import GameState, Job

JOB_FAMILY_STABILITY: dict[str, float] = {
    "doctor": 0.35,
    "teacher": 0.25,
    "developer": 0.10,
    "retail_worker": -0.25,
    "delivery_driver": -0.10,
}


def list_jobs() -> list[JobSpec]:
    return JOBS


def find_job(job_id: str) -> JobSpec | None:
    for j in JOBS:
        if j.job_id == job_id:
            return j
    return None


def apply_for_job(state: GameState, job_id: str) -> tuple[bool, str]:
    """Returns (hired, message). State is mutated only on success."""
    if state.character is None:
        return False, "No character."
    spec = find_job(job_id)
    if spec is None:
        return False, "That job does not exist."
    if state.character.age < spec.min_age:
        return False, f"You are too young to be a {spec.title}."
    if state.stats.smarts < spec.min_smarts:
        return False, f"You failed the interview for {spec.title}. You need to be smarter."
    if not education_meets(state.education.level, spec.min_education):
        return False, f"You need at least {spec.min_education} to be a {spec.title}."

    state.career = Job(job_id=spec.job_id, title=spec.title, salary=spec.salary)
    return True, f"You were hired as a {spec.title}. Your salary is £{spec.salary:,}."


def annual_cashflow(state: GameState, rng: Rng) -> tuple[int, int, str]:
    """Returns (earnings, living_cost, note). State is NOT mutated."""
    if state.character is None or state.character.age < 18:
        return 0, 0, ""
    world = state.world.clamped()
    inflation = world.inflation_index

    base_living = 5_000 + rng.randint(0, 2_000)
    recession_penalty = 600 if world.recession else 0
    living_cost = int((base_living + recession_penalty) * inflation)

    if state.career:
        stability = JOB_FAMILY_STABILITY.get(state.career.job_id, 0.0)
        unemployment_risk = max(0.0, world.unemployment_rate - 0.04)
        salary_hit = min(0.40, max(0.0, unemployment_risk * (1.6 - stability) + (0.12 if world.recession else 0.0) - (0.05 * stability)))
        earnings = int(state.career.salary * (1.0 - salary_hit))
        note = f"You earned £{earnings:,} from your job in a {'recession' if world.recession else 'volatile'} economy."
    else:
        pressure = int(400 * inflation) + (500 if world.recession else 0)
        earnings = -pressure
        note = "You are unemployed and struggling in a weak economy."

    return earnings, max(0, living_cost), note
