"""Job catalogue.

A 'fit' check happens in core.economy. Anything that gates a job (age, smarts,
education level, prior career, criminal record) is declared here as data, not
hardcoded in a controller — keeps the rules visible and tweakable.

Two tracks added in this pass:

- Criminal track: low education, lower smarts floor, much higher pay; UI may
  expose these only if the player engages with criminal events.
- Academic track: gated on University, peaks at Professor.
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
    track: str = "general"  # "general" | "academic" | "criminal" | "executive"


# Ordered roughly by accessibility.
JOBS: list[JobSpec] = [
    # --- General -----------------------------------------------------------
    JobSpec("retail",    "Retail Assistant",         16, 0,  "None",                 15_000),
    JobSpec("barista",   "Barista",                  16, 0,  "None",                 16_000),
    JobSpec("admin",     "Admin Assistant",          18, 40, "Secondary Education",  22_000),
    JobSpec("teacher",   "Primary School Teacher",   21, 65, "Secondary Education",  28_000),
    JobSpec("developer", "Junior Software Developer",18, 75, "Secondary Education",  32_000),
    JobSpec("doctor",    "Junior Doctor",            24, 90, "Secondary Education",  35_000),
    JobSpec("ceo",       "Chief Executive Officer",  35, 85, "Secondary Education", 150_000, track="executive"),

    # --- Academic track ---------------------------------------------------
    JobSpec("ta",        "Teaching Assistant",       20, 70, "University",           24_000, track="academic"),
    JobSpec("researcher","University Researcher",    24, 80, "University",           34_000, track="academic"),
    JobSpec("lecturer",  "Lecturer",                 28, 85, "University",           46_000, track="academic"),
    JobSpec("professor", "Professor",                40, 90, "University",           72_000, track="academic"),

    # --- Criminal track ---------------------------------------------------
    JobSpec("pickpocket", "Pickpocket",              14, 30, "None",                 12_000, track="criminal"),
    JobSpec("dealer",     "Street Dealer",           17, 25, "None",                 28_000, track="criminal"),
    JobSpec("fixer",      "Fixer",                   22, 55, "None",                 55_000, track="criminal"),
    JobSpec("kingpin",    "Crime Boss",              30, 70, "None",                120_000, track="criminal"),
]

EDUCATION_ORDER = ["None", "Primary School", "Secondary School", "Secondary Education", "University"]


def education_meets(have: str, need: str) -> bool:
    try:
        return EDUCATION_ORDER.index(have) >= EDUCATION_ORDER.index(need)
    except ValueError:
        return False


def jobs_by_track(track: str) -> list[JobSpec]:
    return [j for j in JOBS if j.track == track]
