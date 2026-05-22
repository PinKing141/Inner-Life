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
