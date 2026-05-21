"""Education lifecycle: schooling, the final exam, university and postgrad.

- Primary/secondary schooling is age-gated.
- At 18 the player sits a final exam; the grade (blended with smarts) decides
  university admission tier and scholarships.
- University is choice-driven (a popup). While enrolled, tuition is charged
  each year — which simply pushes the bank balance into the negatives for now;
  earnings from a job pay it back over time.
- After an undergraduate degree the player can pursue a master's, then a
  doctorate, from the Career tab.

A richer university system (entry requirements, prestige, course length) is
planned as a later DLC-style extension and slots in around these hooks.
"""
from __future__ import annotations

from core.content import exam as exam_mod
from core.content.courses import field_for_major
from core.rng import Rng
from core.state import FeedEntry, GameState

SECONDARY_GRADUATION_AGE = 18

# Each university-level program: years of study, annual tuition, the label used
# in the graduation popup, and the program that can follow it.
PROGRAMS: dict[str, dict] = {
    "University": {"years": 4, "tuition": 9_250, "label": "undergraduate degree", "next": "Master's Degree"},
    "Master's Degree": {"years": 2, "tuition": 11_000, "label": "master's degree", "next": "Doctorate"},
    "Doctorate": {"years": 3, "tuition": 4_500, "label": "doctorate", "next": None},
}

_UNIVERSITY_NAMES = {
    "Prestigious": ["{city} Imperial University", "Royal University of {city}", "{city} Institute of Technology"],
    "Standard": ["University of {city}", "{city} State University", "{city} Metropolitan University"],
    "Community": ["{city} Community College", "{city} College"],
}


def _university_rng(state: GameState) -> Rng:
    return Rng(state.seed).fork(state.tick).fork(91)


def _generate_university_name(state: GameState, tier: str) -> str:
    city = (state.character.city if state.character else "") or "the City"
    patterns = _UNIVERSITY_NAMES.get(tier) or _UNIVERSITY_NAMES["Standard"]
    return _university_rng(state).choice(patterns).format(city=city)


def tuition_due(edu) -> int:
    prog = PROGRAMS.get(edu.level)
    if not prog:
        return 0
    base = prog["tuition"]
    if edu.level == "University":
        if edu.scholarship == "full":
            return 0
        if edu.scholarship == "partial":
            return base // 2
    return base


def enroll_program(state: GameState, program: str, major: str | None = None) -> None:
    """Enrol the player in a university-level program (undergrad or postgrad)."""
    edu = state.education
    prog = PROGRAMS[program]
    edu.level = program
    edu.in_school = True
    edu.university_dropped_out = False
    edu.study_years_left = prog["years"]
    if major is not None:
        edu.university_major = major
        edu.degree_field = field_for_major(major)
    tier = edu.admitted_tier or "Standard"
    edu.university_name = _generate_university_name(state, tier)


def enroll_university(state: GameState) -> None:
    """Undergraduate enrolment — used by the popup and the pre-set-intent path."""
    enroll_program(state, "University", major=state.education.university_major)


def finalize_exam(state: GameState) -> str:
    """Grade the final exam, set admission tier and scholarship, and prompt the
    university choice if the player was admitted."""
    edu = state.education
    ex = state.exam or {}
    total = max(0, len(ex.get("questions", [])))
    correct = ex.get("correct", 0)
    smarts = state.stats.smarts
    grade = "F" if ex.get("caught") else exam_mod.grade_for(correct, total, smarts)
    adm = exam_mod.admission_for(grade)

    edu.exam_taken = True
    edu.awaiting_exam = False
    edu.final_school_grade = grade
    edu.exam_correct = correct
    edu.admitted_tier = adm["tier"]
    edu.scholarship = adm["scholarship"] if adm["tier"] else "none"
    if ex:
        ex["finished"] = True

    if adm["tier"]:
        edu.awaiting_university_choice = True
        return (
            f"Your final school grade was {grade}. "
            f"You were admitted to a {adm['tier'].lower()} university"
            + (f" with a {adm['scholarship']} scholarship." if adm["scholarship"] != "none" else ".")
        )
    return f"Your final school grade was {grade}. You did not get a university place."


def _award_degree(state: GameState) -> str:
    edu = state.education
    prog = PROGRAMS[edu.level]
    if edu.level == "University":
        edu.degree_completed = True
    elif edu.level == "Master's Degree":
        edu.masters_completed = True
    elif edu.level == "Doctorate":
        edu.doctorate_completed = True
    edu.in_school = False
    edu.study_years_left = 0
    edu.degree_award_pending = True
    edu.degree_award_label = prog["label"]
    major = edu.university_major or "an undeclared subject"
    uni = edu.university_name or "university"
    return f"You graduated from {uni} with a {prog['label']} in {major}."


def tick(state: GameState) -> str | None:
    """Advance education state. Returns a message if anything changed."""
    if state.character is None:
        return None
    age = state.character.age
    edu = state.education

    if age == 5:
        edu.level = "Primary School"
        edu.in_school = True
        return "You have started Primary School."
    if age == 11:
        edu.level = "Secondary School"
        edu.in_school = True
        return "You have started Secondary School."
    if age == SECONDARY_GRADUATION_AGE and edu.in_school and edu.level != "University":
        edu.level = "Secondary Education"
        edu.in_school = False
        if edu.university_intent == "attend" and not edu.university_dropped_out:
            enroll_university(state)
            major = edu.university_major or "an undeclared course"
            return (
                "You graduated secondary school. "
                f"You enrolled in {major} course at university."
            )
        if edu.university_intent == "skip":
            return "You graduated secondary school. You chose not to attend university."
        # Undecided: sit the final exam first (the UI prompts the quiz).
        edu.awaiting_exam = True
        if state.exam is None:
            first = state.character.first_name
            state.exam = exam_mod.generate_exam(_university_rng(state), first)
        return "You graduated secondary school. It's time for your final exams."

    # Headless safety net: if the exam was never taken, auto-grade it so the
    # simulation never stalls waiting on a popup.
    if edu.awaiting_exam and age > SECONDARY_GRADUATION_AGE:
        return finalize_exam(state)

    # Ongoing university study: charge tuition, count down, graduate.
    if edu.in_school and edu.level in PROGRAMS:
        state.money -= tuition_due(edu)
        edu.study_years_left -= 1
        if edu.study_years_left <= 0:
            return _award_degree(state)

    return None
