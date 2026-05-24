"""Canonical activity effects — the single source of truth for what 'study',
'gym', 'doctor' and family time do to a character.

Both the controller (real player actions) and the headless auto-play policy
used by the observatory call these, so there is no second copy of the numbers
to drift. Each returns (ok, log); state is mutated only as described.
"""
from __future__ import annotations

from core import relationships
from core.state import GameState

GYM_COST = 30
DOCTOR_COST = 100

# Per-activity unlock ages — exposed via the snapshot so the UI can show
# locked rows with an "Age N" badge instead of letting players tap into a
# silent rejection. Single source of truth.
STUDY_MIN_AGE = 5
GYM_MIN_AGE = 12
DOCTOR_MIN_AGE = 0
FAMILY_TIME_MIN_AGE = 0


def study(state: GameState) -> tuple[bool, str]:
    state.stats.smarts = min(100, state.stats.smarts + 2)
    state.stats.happiness = max(0, state.stats.happiness - 2)
    return True, "You studied hard. You feel smarter, but a bit bored."


def gym(state: GameState) -> tuple[bool, str]:
    if state.money < GYM_COST:
        return False, "You cannot afford the gym."
    state.money -= GYM_COST
    state.stats.health = min(100, state.stats.health + 3)
    state.stats.looks = min(100, state.stats.looks + 1)
    return True, "You went to the gym. It cost £30."


def doctor(state: GameState) -> tuple[bool, str]:
    if state.money < DOCTOR_COST:
        return False, "You cannot afford a private doctor."
    state.money -= DOCTOR_COST
    state.stats.health = min(100, state.stats.health + 15)
    return True, "You visited a private doctor. It cost £100 but you feel much better."


def family_time(state: GameState) -> tuple[bool, str]:
    relationships.spend_time_with_family(state)
    state.stats.happiness = min(100, state.stats.happiness + 5)
    return True, "You spent quality time with your family."


# Verb name (as the UI/bridge uses) -> effect function.
BY_KIND = {"study": study, "gym": gym, "doctor": doctor, "spend_time": family_time}


# UI descriptors — read by the controller into the snapshot so the front-end
# can render the Activities screen without inventing its own copy of the data.
DESCRIPTORS = [
    {"id": "doctor", "title": "Visit the Doctor",
     "subtitle": f"A check-up — costs £{DOCTOR_COST}.",
     "unlock": DOCTOR_MIN_AGE, "icon": "doctor", "accent": "health"},
    {"id": "study", "title": "Study Hard",
     "subtitle": "Boost your smarts; a little bored.",
     "unlock": STUDY_MIN_AGE, "icon": "book", "accent": "smarts"},
    {"id": "gym", "title": "Go to the Gym",
     "subtitle": f"Train for health and looks — £{GYM_COST}.",
     "unlock": GYM_MIN_AGE, "icon": "dumbbell", "accent": "health"},
    {"id": "spend_time", "title": "Spend Time with Family",
     "subtitle": "Strengthen bonds with relatives.",
     "unlock": FAMILY_TIME_MIN_AGE, "icon": "heart", "accent": "happy"},
]


def list_descriptors() -> list[dict]:
    return [dict(d) for d in DESCRIPTORS]
