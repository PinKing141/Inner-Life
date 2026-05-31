"""Phase 2 — NPC↔NPC social graph.

`GameState.relationships` is the *player-facing* slice of the social world.
This module adds the missing layer: edges between NPCs that the player
isn't necessarily a node of. Mum and Dad are spouses, Mum has a best friend,
that best friend has a sibling who works with Dad — the kind of structure
that lets drama emerge from *triangles* rather than star-graphs around the
player.

Design rules:

- Undirected graph. Edges are canonicalised so (a, b) and (b, a) are the
  same edge — there's only ever one record per pair.
- Edges live on `state.social_edges` and serialise via to_dict / from_dict
  like every other piece of state. Determinism is preserved.
- Agent liveness is *not* a property of the edge; lookups that need
  living-only graphs (e.g. predicate filtering) check `Agent.alive`
  at query time. Death prunes nothing automatically — a dead person can
  still have *been* someone's best friend, and that history matters for
  causal narrative reconstruction later.
- This module never mutates Agents or Relationships — it is purely the
  graph layer. Whoever calls `add_edge` is the system responsible for
  the meaning.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.state import GameState


# Recognised edge kinds today. Open-ended: anything can be passed; this
# constant just documents the in-use vocabulary so events / predicates and
# the seeding code agree on terminology.
KIND_SPOUSE = "spouse"
KIND_FRIEND = "friend"
KIND_COWORKER = "coworker"
KIND_RIVAL = "rival"


@dataclass
class SocialEdge:
    """An undirected, weighted relationship between two NPCs.

    Canonical form: ``a < b`` so each pair has exactly one record. Use the
    module-level helpers (add_edge / get_edge / neighbors) rather than
    constructing instances directly — they enforce the ordering.
    """

    a: int       # smaller npc_id
    b: int       # larger npc_id
    kind: str    # see KIND_* constants
    strength: int = 50  # 0..100

    def involves(self, npc_id: int) -> bool:
        return npc_id == self.a or npc_id == self.b

    def other(self, npc_id: int) -> int:
        """Given one endpoint, return the other. Raises if npc_id isn't on
        the edge — that's a caller bug worth surfacing."""
        if npc_id == self.a:
            return self.b
        if npc_id == self.b:
            return self.a
        raise ValueError(f"npc_id {npc_id} is not an endpoint of this edge")

    def to_dict(self) -> dict:
        return {"a": self.a, "b": self.b, "kind": self.kind, "strength": self.strength}

    @classmethod
    def from_dict(cls, d: dict) -> "SocialEdge":
        # Re-canonicalise on load: tolerates older saves that wrote (b, a),
        # so the invariant holds even if the persistence format ever drifted.
        a, b = int(d["a"]), int(d["b"])
        if a > b:
            a, b = b, a
        return cls(a=a, b=b, kind=str(d.get("kind", KIND_FRIEND)),
                   strength=int(d.get("strength", 50)))


# --- Mutation -------------------------------------------------------------


def _canonical(a: int, b: int) -> tuple[int, int]:
    return (a, b) if a < b else (b, a)


def add_edge(state: GameState, a: int, b: int, kind: str, strength: int = 50) -> SocialEdge:
    """Insert or update an edge between two NPCs.

    Self-loops (a == b) are rejected — a person can't be edge-related to
    themselves. If an edge already exists, ``kind`` and ``strength`` are
    overwritten (so a friendship that becomes a rivalry is a single edge,
    not two). Returns the edge.
    """
    if a == b:
        raise ValueError(f"social edge cannot loop on a single npc ({a})")
    ca, cb = _canonical(a, b)
    existing = get_edge(state, ca, cb)
    if existing is not None:
        existing.kind = kind
        existing.strength = max(0, min(100, strength))
        return existing
    edge = SocialEdge(a=ca, b=cb, kind=kind, strength=max(0, min(100, strength)))
    state.social_edges.append(edge)
    return edge


def remove_edge(state: GameState, a: int, b: int) -> bool:
    """Drop the edge between two NPCs. Returns whether one was actually removed."""
    ca, cb = _canonical(a, b)
    for i, e in enumerate(state.social_edges):
        if e.a == ca and e.b == cb:
            del state.social_edges[i]
            return True
    return False


def remove_edges_of(state: GameState, npc_id: int) -> int:
    """Drop every edge touching ``npc_id``. Returns the number removed.

    Not called on death by default (dead NPCs keep their historical edges),
    but available for explicit pruning when the social history shouldn't
    persist — e.g. erasing a removed save migration."""
    kept = [e for e in state.social_edges if not e.involves(npc_id)]
    removed = len(state.social_edges) - len(kept)
    state.social_edges = kept
    return removed


def bump_strength(state: GameState, a: int, b: int, delta: int) -> Optional[SocialEdge]:
    """Adjust an edge's strength by ``delta``, clamped to 0..100.
    No-op if the edge doesn't exist (returns None) — callers decide whether
    that means create-from-scratch or skip."""
    e = get_edge(state, a, b)
    if e is None:
        return None
    e.strength = max(0, min(100, e.strength + delta))
    return e


# --- Queries --------------------------------------------------------------


def get_edge(state: GameState, a: int, b: int) -> Optional[SocialEdge]:
    ca, cb = _canonical(a, b)
    for e in state.social_edges:
        if e.a == ca and e.b == cb:
            return e
    return None


def edges_of(state: GameState, npc_id: int, *, kind: str | None = None) -> list[SocialEdge]:
    """Every edge touching ``npc_id``, optionally filtered by kind."""
    return [e for e in state.social_edges if e.involves(npc_id) and (kind is None or e.kind == kind)]


def neighbors(state: GameState, npc_id: int, *, kind: str | None = None) -> list[int]:
    """The NPC ids adjacent to ``npc_id``. Stable order: by npc_id ascending,
    so callers can write deterministic code over the result."""
    out = sorted({e.other(npc_id) for e in edges_of(state, npc_id, kind=kind)})
    return out


def are_connected(state: GameState, a: int, b: int, *, kind: str | None = None) -> bool:
    """Whether ``a`` and ``b`` share an edge (of the optional kind)."""
    e = get_edge(state, a, b)
    return e is not None and (kind is None or e.kind == kind)


def mutual_neighbors(state: GameState, a: int, b: int) -> list[int]:
    """NPC ids adjacent to BOTH ``a`` and ``b`` — the triangle-completers.

    The single most useful query for emergent drama: 'mum's best friend
    is also dad's coworker', 'two of your friends know each other'. Stable
    sort by npc_id."""
    na = set(neighbors(state, a))
    nb = set(neighbors(state, b))
    return sorted(na & nb)
