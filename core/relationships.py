"""Social graph (player-facing slice).

`Relationship` is a thin player-side view of an `Agent` (see core.agents).
This module owns the player's initial family, the bump/drift loop, and any
direct player↔NPC mutation. Anything that ticks an NPC itself lives in
`core.agents`.
"""
from __future__ import annotations

from core.content import names as names_mod
from core.rng import Rng
from core.state import GameState, Relationship


def seed_family(
    state: GameState,
    rng: Rng | None = None,
    *,
    mother_name: str | None = None,
    father_name: str | None = None,
) -> None:
    """Spawn the player's parents at birth with culture-appropriate names."""
    rng = rng or Rng(state.seed ^ 0xA1B2C3)
    country = state.character.country if state.character else ""
    surname = state.character.last_name if state.character else ""

    mum_first = names_mod.random_forename(country, "Female", rng.fork(1))
    dad_first = names_mod.random_forename(country, "Male", rng.fork(2))
    # Keep parents on the player's surname for clarity in the early UI.
    mum_name = mother_name or f"{mum_first} {surname}".strip()
    dad_name = father_name or f"{dad_first} {surname}".strip()

    state.relationships.append(Relationship(npc_id=1, name=mum_name, kind="Mother", relationship=90))
    state.relationships.append(Relationship(npc_id=2, name=dad_name, kind="Father", relationship=90))


def spend_time_with_family(state: GameState) -> None:
    for r in state.relationships:
        if r.kind in ("Mother", "Father", "Sibling") and r.alive:
            r.relationship = min(100, r.relationship + 5)


def annual_drift(state: GameState) -> None:
    """Relationships decay slightly if not actively maintained."""
    for r in state.relationships:
        if not r.alive:
            continue
        r.relationship = max(0, r.relationship - 1)


# --- Isolation consequence (decay vertical slice) ---
# Decay already nibbles relationships every year; this gives that decay teeth.
# When the player has no remaining strong tie, isolation costs happiness — so
# letting the social graph rot is now a real pressure, not just a number going
# down. The narrative line is rate-limited (via tick) so it doesn't spam.
LONELY_KINDS = ("Mother", "Father", "Sibling", "Partner", "Friend")
LONELY_THRESHOLD = 25
LONELY_PENALTY = 2


def loneliness_tick(state: GameState) -> str | None:
    """Apply a happiness penalty when the player is socially isolated.

    Returns a feed-worthy note on the years it surfaces, else None. The
    penalty itself applies every isolated year regardless of the note.
    """
    if state.character is None:
        return None
    close = [r for r in state.relationships if r.alive and r.kind in LONELY_KINDS]
    support = max((r.relationship for r in close), default=0)
    if support >= LONELY_THRESHOLD:
        return None
    state.stats.happiness = max(0, state.stats.happiness - LONELY_PENALTY)
    if state.tick % 5 == 0:
        return "You feel increasingly lonely and disconnected from those around you."
    return None


GIFT_COST = 50

INTERACTIONS = ("talk", "compliment", "argue", "gift")


def interact(state: GameState, npc_id: int, action: str) -> tuple[bool, str]:
    """Player-initiated interaction with a known NPC. Returns (ok, message).

    State is only mutated on success. Effects are deterministic for now."""
    rel = next((r for r in state.relationships if r.npc_id == npc_id), None)
    if rel is None:
        return False, "You don't know that person."
    name = rel.name
    if not rel.alive:
        return False, f"{name} has passed away."

    if action == "talk":
        rel.relationship = min(100, rel.relationship + 3)
        state.stats.happiness = min(100, state.stats.happiness + 1)
        return True, f"You had a nice chat with {name}."
    if action == "compliment":
        rel.relationship = min(100, rel.relationship + 5)
        return True, f"You complimented {name}. They appreciated it."
    if action == "argue":
        rel.relationship = max(0, rel.relationship - 8)
        state.stats.happiness = max(0, state.stats.happiness - 3)
        return True, f"You got into an argument with {name}."
    if action == "gift":
        if state.money < GIFT_COST:
            return False, f"You can't afford a gift for {name}."
        state.money -= GIFT_COST
        rel.relationship = min(100, rel.relationship + 10)
        return True, f"You gave {name} a gift. It cost £{GIFT_COST}."
    return False, "You can't do that."
