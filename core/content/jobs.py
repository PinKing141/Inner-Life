"""Job catalogue.

A 'fit' check happens in core.economy. Anything that gates a job (age, smarts,
education level, prior career, criminal record) is declared here as data, not
hardcoded in a controller — keeps the rules visible and tweakable.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class JobSpec:
    job_id: str
    title: str
    min_age: int
    min_smarts: int
    min_education: str  # one of None, Primary School, Secondary Education, University
    salary: int


# Ordered roughly by accessibility.
JOBS: list[JobSpec] = [
    JobSpec("retail", "Retail Assistant", 16, 0, "None", 15_000),
    JobSpec("barista", "Barista", 16, 0, "None", 16_000),
    JobSpec("admin", "Admin Assistant", 18, 40, "Secondary Education", 22_000),
    JobSpec("teacher", "Primary School Teacher", 21, 65, "Secondary Education", 28_000),
    JobSpec("developer", "Junior Software Developer", 18, 75, "Secondary Education", 32_000),
    JobSpec("doctor", "Junior Doctor", 24, 90, "Secondary Education", 35_000),
    JobSpec("ceo", "Chief Executive Officer", 35, 85, "Secondary Education", 150_000),
]

EDUCATION_ORDER = ["None", "Primary School", "Secondary School", "Secondary Education", "University"]


def education_meets(have: str, need: str) -> bool:
    try:
        return EDUCATION_ORDER.index(have) >= EDUCATION_ORDER.index(need)
    except ValueError:
        return False
