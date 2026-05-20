"""Causal-chain schema helpers (v1).

All cause nodes written to ``GameState.causal_chain`` should pass through this
module so required fields stay consistent and renderer assumptions remain true.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.state import GameState

SCHEMA_VERSION = 1


@dataclass(frozen=True)
class CauseNode:
    """Structured causal-chain node (schema v1)."""

    id: str
    kind: str
    tick: int
    parent_id: str | None
    source: str
    details: dict[str, Any]
    schema_version: int = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "tick": self.tick,
            "parent_id": self.parent_id,
            "source": self.source,
            "details": dict(self.details),
            "schema_version": self.schema_version,
        }


def latest_cause_id(state: GameState) -> str | None:
    """Return most recent cause id, preferring feed linkage for chronology."""
    for entry in reversed(state.feed):
        if entry.cause_id:
            return entry.cause_id
    for node in reversed(state.causal_chain):
        if isinstance(node, dict) and node.get("id"):
            return str(node["id"])
    return None


def append_cause(
    state: GameState,
    *,
    node_id: str,
    kind: str,
    source: str,
    details: dict[str, Any],
    parent_id: str | None = None,
) -> dict[str, Any]:
    node = CauseNode(
        id=node_id,
        kind=kind,
        tick=state.tick,
        parent_id=parent_id if parent_id is not None else latest_cause_id(state),
        source=source,
        details=details,
    ).to_dict()
    state.causal_chain.append(node)
    return node
