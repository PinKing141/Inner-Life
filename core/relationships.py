"""Social graph.

Today this is a flat list (mirrors the React version). The deeper version
should make NPCs first-class with their own stats, goals, and yearly ticks,
and friendships should be edges in a graph so triangles emerge naturally.
That work is queued — see docs/ROADMAP.md.
"""
from __future__ import annotations

from core.state import GameState, Relationship


def seed_family(state: GameState) -> None:
    """Spawn the player's parents at birth."""
    state.relationships.append(Relationship(npc_id=1, name="Mum", kind="Mother", relationship=90))
    state.relationships.append(Relationship(npc_id=2, name="Dad", kind="Father", relationship=90))


def spend_time_with_family(state: GameState) -> None:
    for r in state.relationships:
        if r.kind in ("Mother", "Father", "Sibling"):
            r.relationship = min(100, r.relationship + 5)


def annual_drift(state: GameState) -> None:
    """Relationships decay slightly if not actively maintained."""
    for r in state.relationships:
        r.relationship = max(0, r.relationship - 1)
