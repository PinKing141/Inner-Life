"""Event engine.

Two responsibilities:

1. Each tick (age-up), roll for a random event from the catalogue.
2. When the player picks a choice, apply its effects to state and write a
   feed entry with a `cause_id` so the causal chain stays intact.

Notes for later: events should eventually consume *state* (not just age) so
'teen_party' only fires if you actually have school-age friends, etc.
"""
from __future__ import annotations

from typing import Optional

from core.content.events import EVENTS
from core.predicates import evaluate as evaluate_predicates
from core.rng import Rng
from core.state import FeedEntry, GameState, Stats


def roll_event(state: GameState, rng: Rng) -> Optional[dict]:
    """Try to fire one event this tick. Returns the chosen event dict, or None.

    Filters by age window first, then by the optional ``predicates`` field on
    each event (see core.predicates) — this is what makes careers, wealth,
    and stats actually gate which beats can fire.
    """
    if state.character is None:
        return None
    age = state.character.age
    candidates = [
        e for e in EVENTS
        if e["min_age"] <= age <= e["max_age"]
        and evaluate_predicates(e.get("predicates"), state)
    ]
    if not candidates:
        return None
    # Single-roll model: shuffle candidates and pick the first whose prob hits.
    # Keeps event count per year low. Swap for a deck/cooldown model later.
    rng.choice  # ensure import
    shuffled = list(candidates)
    # deterministic shuffle
    for i in range(len(shuffled) - 1, 0, -1):
        j = rng.randint(0, i)
        shuffled[i], shuffled[j] = shuffled[j], shuffled[i]
    for e in shuffled:
        if rng.chance(e["prob"]):
            return e
    return None


def get_event(event_id: str) -> Optional[dict]:
    for e in EVENTS:
        if e["id"] == event_id:
            return e
    return None


def apply_effects(state: GameState, effects: dict) -> None:
    s = state.stats
    s.happiness += effects.get("happiness", 0)
    s.health += effects.get("health", 0)
    s.smarts += effects.get("smarts", 0)
    s.looks += effects.get("looks", 0)
    state.stats = s.clamped()
    if "money" in effects:
        state.money += effects["money"]


def _apply_side_effect(state: GameState, name: str) -> None:
    """Side-effects are non-numeric mutations (e.g. clearing a job)."""
    if name == "lose_job":
        state.career = None
    elif name == "leave_school":
        state.education.in_school = False


def resolve_choice(state: GameState, event_id: str, choice_index: int) -> None:
    """Apply a chosen branch and log it. Records causal edges."""
    event = get_event(event_id)
    if event is None:
        return
    if choice_index < 0 or choice_index >= len(event["choices"]):
        return
    choice = event["choices"][choice_index]

    cause_id = f"event:{event_id}:{state.tick}"
    state.causal_chain.append({
        "id": cause_id,
        "kind": "event_choice",
        "event_id": event_id,
        "choice": choice["text"],
        "tick": state.tick,
    })

    apply_effects(state, choice.get("effects", {}))
    side = choice.get("side_effect")
    if side:
        _apply_side_effect(state, side)

    # Classify the feed entry by the net direction of the effects.
    eff = choice.get("effects", {})
    net = sum(v for v in eff.values() if isinstance(v, int))
    kind = "good" if net > 0 else "bad" if net < 0 else "neutral"

    state.feed.append(FeedEntry(
        age=state.character.age if state.character else 0,
        text=choice["log"],
        kind=kind,
        cause_id=cause_id,
        entry_id=f"feed:{state.tick}:{event_id}",
    ))
    state.pending_event_id = None
