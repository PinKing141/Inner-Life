"""University course catalogue.

A first-pass list of undergraduate courses. Each course belongs to a broad
*field*; jobs that require a degree are gated on the field (see
``JobSpec.required_field`` in core.content.jobs), so a Fine Art graduate can't
walk into a Research Scientist role.

This is intentionally a flat data list — a richer university system (entry
requirements, course length, prestige, scholarships) is planned as a later
DLC-style extension and slots in here without touching the simulation.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Course:
    major: str
    field: str


COURSES: list[Course] = [
    Course("Medicine", "medicine"),
    Course("Nursing", "medicine"),
    Course("Physics", "science"),
    Course("Chemistry", "science"),
    Course("Biology", "science"),
    Course("Mathematics", "science"),
    Course("Computer Science", "technology"),
    Course("Software Engineering", "technology"),
    Course("Mechanical Engineering", "engineering"),
    Course("Civil Engineering", "engineering"),
    Course("Law", "law"),
    Course("Business Management", "business"),
    Course("Economics", "business"),
    Course("Accounting", "business"),
    Course("Psychology", "social_science"),
    Course("Sociology", "social_science"),
    Course("History", "humanities"),
    Course("English Literature", "humanities"),
    Course("Philosophy", "humanities"),
    Course("Fine Art", "arts"),
    Course("Music", "arts"),
    Course("Drama", "arts"),
    Course("Education Studies", "education"),
]


def field_for_major(major: str) -> str:
    """Return the field a course belongs to, or '' if it isn't recognised."""
    for c in COURSES:
        if c.major == major:
            return c.field
    return ""


def list_courses_for_ui() -> list[dict]:
    return [{"major": c.major, "field": c.field} for c in COURSES]
