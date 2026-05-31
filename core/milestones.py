"""Life-milestone popups — turning 18, 30, 50, 65, 100.

Milestones are deterministic, not rolled like events. The sim's age_up
calls `check(state)` after the year's other systems have run; if the
character has crossed a threshold for the first time this life,
`state.pending_milestone` is set and the UI raises a modal next tick.

Why a separate channel instead of using the event engine? Events compete
in a single shuffle-then-roll per tick, so a 50% event could displace a
"happy 18th" milestone. Milestones must always fire on the right year —
they're narrative anchors, not random drama.

Per-life: `milestones_seen` is part of GameState and resets on heir
transitions (continue_as_heir) so each new generation gets to mark its
own 18, 30, 50, etc.
"""
from __future__ import annotations

from core.state import GameState


# Each entry: (age, title, subtitle, kind). `kind` maps to the modal
# accent / icon so the UI can paint a happy 18th differently from a
# sober 65th.
MILESTONES: list[dict] = [
    {"age": 18,  "id": "milestone:18",  "title": "You're an adult.",
     "subtitle": "The world expects more of you now. The world isn't always right.",
     "kind": "coming_of_age"},
    {"age": 30,  "id": "milestone:30",  "title": "Welcome to your 30s.",
     "subtitle": "Your back has opinions. Your tastes have narrowed in good ways.",
     "kind": "decade"},
    {"age": 50,  "id": "milestone:50",  "title": "Half a century.",
     "subtitle": "Fifty laps around the sun. You know yourself better than most.",
     "kind": "decade"},
    {"age": 65,  "id": "milestone:65",  "title": "Retirement age.",
     "subtitle": "You don't have to work anymore. You probably will anyway.",
     "kind": "retirement"},
    {"age": 100, "id": "milestone:100", "title": "A century.",
     "subtitle": "One hundred years. The world has changed around you, and you with it.",
     "kind": "centenarian"},
]

_BY_AGE: dict[int, dict] = {m["age"]: m for m in MILESTONES}


def check(state: GameState) -> dict | None:
    """If the current character's age matches a milestone they haven't
    seen this life, queue it on `state.pending_milestone` and return
    it. Otherwise return None. Safe to call every tick.

    Refuses to queue a second milestone while one is still pending —
    the UI must acknowledge the current popup first. (Realistically
    milestones are 5+ years apart so this only matters if the player
    leaves a milestone unacknowledged across age_ups.)"""
    if state.character is None:
        return None
    if state.pending_milestone is not None:
        return None
    age = state.character.age
    m = _BY_AGE.get(age)
    if m is None or age in state.milestones_seen:
        return None
    state.pending_milestone = dict(m)
    state.milestones_seen.append(age)
    return state.pending_milestone


def acknowledge(state: GameState) -> None:
    """Clear the pending milestone — the player has dismissed the modal."""
    state.pending_milestone = None
