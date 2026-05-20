"""Economy: career, salary, living costs.

The annual budget pass runs from core.sim.tick. This module just declares the
rules for whether a job application succeeds and what the yearly cashflow
looks like.
"""
from __future__ import annotations

from core.content.jobs import JOBS, JobSpec, education_meets
from core.rng import Rng
from core.state import GameState, Job


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
    earnings = state.career.salary if state.career else 0
    living_cost = 5_000 + rng.randint(0, 2_000)
    if state.career:
        note = f"You earned £{earnings:,} from your job."
    else:
        note = "You are unemployed and struggling."
    return earnings, living_cost, note
