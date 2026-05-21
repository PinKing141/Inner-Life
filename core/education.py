"""Education lifecycle progression.

Schooling is age-gated. University is choice-driven: at secondary graduation
the player is prompted (a popup in the UI) to pick a course and enrol, or skip.
While enrolled, student debt accrues each year; the undergraduate degree is
awarded after four years.

A richer university system (entry requirements, course length, prestige) is
planned as a later DLC-style extension and slots in around these hooks.
"""
from __future__ import annotations

from core.content.courses import field_for_major
from core.rng import Rng
from core.state import GameState

TUITION_PER_YEAR = 9_250
DEBT_INTEREST = 0.03
UNIVERSITY_GRADUATION_AGE = 22

_UNIVERSITY_NAME_PATTERNS = [
    "University of {city}",
    "{city} State University",
    "{city} Metropolitan University",
    "Royal {city} University",
    "{city} College",
]


def _university_rng(state: GameState) -> Rng:
    return Rng(state.seed).fork(state.tick).fork(91)


def _generate_university_name(state: GameState) -> str:
    city = (state.character.city if state.character else "") or "the City"
    return _university_rng(state).choice(_UNIVERSITY_NAME_PATTERNS).format(city=city)


def enroll_university(state: GameState) -> None:
    """Put the player into university now. Used by both the pre-set-intent path
    (at secondary graduation) and the popup path (player chooses on graduation)."""
    edu = state.education
    edu.level = "University"
    edu.in_school = True
    edu.university_dropped_out = False
    if not edu.university_name:
        edu.university_name = _generate_university_name(state)
    edu.degree_field = field_for_major(edu.university_major)


def _accrue_student_debt(state: GameState) -> None:
    edu = state.education
    if edu.student_debt > 0:
        edu.student_debt = int(edu.student_debt * (1.0 + DEBT_INTEREST))
    if edu.level == "University" and edu.in_school:
        edu.student_debt += TUITION_PER_YEAR


def tick(state: GameState) -> str | None:
    """Advance education state. Returns a message if anything changed."""
    if state.character is None:
        return None
    age = state.character.age
    edu = state.education
    msg: str | None = None

    if age == 5:
        edu.level = "Primary School"
        edu.in_school = True
        msg = "You have started Primary School."
    elif age == 11:
        edu.level = "Secondary School"
        edu.in_school = True
        msg = "You have started Secondary School."
    elif age == 18 and edu.in_school:
        edu.level = "Secondary Education"
        edu.in_school = False
        if edu.university_intent == "attend" and not edu.university_dropped_out:
            enroll_university(state)
            major = edu.university_major or "an undeclared course"
            msg = (
                "You graduated secondary school. "
                f"You enrolled in {major} course at university."
            )
        elif edu.university_intent == "skip":
            msg = "You graduated secondary school. You chose not to attend university."
        else:
            # Undecided — let the UI prompt the course picker.
            edu.awaiting_university_choice = True
            msg = "You graduated secondary school."
    elif age >= UNIVERSITY_GRADUATION_AGE and edu.level == "University" and edu.in_school:
        edu.in_school = False
        edu.degree_completed = True
        edu.degree_award_pending = True
        major = edu.university_major or "an undeclared subject"
        uni = edu.university_name or "university"
        msg = f"You graduated from {uni} with an undergraduate degree in {major}."

    _accrue_student_debt(state)
    return msg
