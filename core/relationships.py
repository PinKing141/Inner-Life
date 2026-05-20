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
