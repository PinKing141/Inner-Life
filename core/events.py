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
from core.rng import Rng
from core.state import FeedEntry, GameState, Stats


def roll_event(state: GameState, rng: Rng) -> Optional[dict]:
    """Try to fire one event this tick. Returns the chosen event dict, or None.

    Non-repeatable events (the default) are filtered once their id appears in
    state.fired_event_ids — life-once moments like 'first_word' should never
    fire twice.
    """
    if state.character is None:
        return None
    age = state.character.age
    fired = set(state.fired_event_ids)
    candidates = [
        e for e in EVENTS
        if e["min_age"] <= age <= e["max_age"]
        and (e.get("repeatable", False) or e["id"] not in fired)
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
    if event_id not in state.fired_event_ids:
        state.fired_event_ids.append(event_id)
