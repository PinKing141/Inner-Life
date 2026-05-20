"""Education lifecycle progression.

Currently age-gated; deeper version would route through choices (drop out,
private vs state, university course, etc.).
"""
from __future__ import annotations

from core.state import GameState


def tick(state: GameState) -> str | None:
    """Advance education state. Returns a message if anything changed."""
    if state.character is None:
        return None
    age = state.character.age

    if age == 5:
        state.education.level = "Primary School"
        state.education.in_school = True
        return "You have started Primary School."
    if age == 11:
        state.education.level = "Secondary School"
        state.education.in_school = True
        return "You have started Secondary School."
    if age == 18 and state.education.in_school:
        state.education.level = "Secondary Education"
        state.education.in_school = False
        return "You have graduated from Secondary School."
    if age == 19 and state.education.university_intent == "attend" and not state.education.university_dropped_out:
        state.education.level = "University"
        state.education.in_school = True
        major = state.education.university_major or "an undeclared course"
        return f"You started university, studying {major}."
    return None
