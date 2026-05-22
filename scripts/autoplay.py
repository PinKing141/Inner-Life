"""Shared headless auto-play policy.

The observatory and the mock-snapshot generator both need to drive a life
without a human. This is the single home for that policy so the constants
(job eligibility, self-care choices) are not copied and hand-synced. It
consumes canonical rules from core — activity effects come straight from
core.activities, so there is no mirrored set of numbers to drift.
"""
from __future__ import annotations

from core import activities
from core.content.jobs import JOBS, education_meets
from core.state import GameState


def best_eligible_job(state: GameState):
    """Highest-salary non-criminal job whose hard requirements are met."""
    elig = [
        j for j in JOBS
        if j.track != "criminal"
        and state.character.age >= j.min_age
        and state.stats.smarts >= j.min_smarts
        and education_meets(state.education.level, j.min_education)
        and not (j.required_field and (not state.education.degree_completed
                                       or state.education.degree_field != j.required_field))
    ]
    return max(elig, key=lambda j: j.salary) if elig else None


def apply_self_care(state: GameState) -> None:
    """A character actively maintaining themselves: healthcare when affordable,
    study while young, family time. Effects come from canonical core.activities;
    the policy (what to attempt) is the only thing that lives here."""
    if state.stats.health < 90:
        ok, _ = activities.doctor(state)
        if not ok:
            activities.gym(state)
    if state.character.age < 25:
        activities.study(state)
    activities.family_time(state)
