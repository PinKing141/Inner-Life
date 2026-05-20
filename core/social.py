"""NPC<->NPC social simulation.

Lightweight v1 system:
- graph edges between NPC agents with constrained relationship types
- motif-driven archetype events (triangle, isolation, nepotism)
- rumor packets that propagate with attenuation/TTL
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from core.rng import Rng
from core.state import FeedEntry, GameState

RelationshipType = Literal["friend", "family", "enemy", "coworker"]


@dataclass
class SocialEdge:
    source_id: int
    target_id: int
    relation_type: RelationshipType
    strength: int = 50
    trust: int = 50
    contact_rate: float = 0.25

    def to_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type,
            "strength": self.strength,
            "trust": self.trust,
            "contact_rate": self.contact_rate,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SocialEdge":
        rel = d.get("relation_type", "friend")
        if rel not in ("friend", "family", "enemy", "coworker"):
            rel = "friend"
        return cls(
            source_id=d["source_id"],
            target_id=d["target_id"],
            relation_type=rel,
            strength=d.get("strength", 50),
            trust=d.get("trust", 50),
            contact_rate=d.get("contact_rate", 0.25),
        )


@dataclass
class Rumour:
    topic: str
    stance: Literal["positive", "negative", "neutral"]
    origin_id: int
    current_id: int
    credibility: float = 0.8
    intensity: float = 1.0
    ttl: int = 4
    seen_by: list[int] | None = None

    def to_dict(self) -> dict:
        return {
            "topic": self.topic,
            "stance": self.stance,
            "origin_id": self.origin_id,
            "current_id": self.current_id,
            "credibility": self.credibility,
            "intensity": self.intensity,
            "ttl": self.ttl,
            "seen_by": list(self.seen_by or []),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Rumour":
        return cls(
            topic=d.get("topic", ""),
            stance=d.get("stance", "neutral"),
            origin_id=d.get("origin_id", 0),
            current_id=d.get("current_id", 0),
            credibility=d.get("credibility", 0.8),
            intensity=d.get("intensity", 1.0),
            ttl=d.get("ttl", 0),
            seen_by=list(d.get("seen_by", [])),
        )


def _add_edge(state: GameState, source_id: int, target_id: int, relation_type: RelationshipType, rng: Rng) -> None:
    strength = 45 + rng.randint(0, 45)
    trust = 40 + rng.randint(0, 50)
    contact = 0.1 + (strength / 100) * 0.5
    state.social_edges.append(SocialEdge(source_id, target_id, relation_type, strength, trust, contact))


def seed_social_graph(state: GameState, rng: Rng) -> None:
    """Create a sparse small-world-ish graph among existing NPCs."""
    if state.social_edges:
        return
    ids = [a.npc_id for a in state.agents if a.alive]
    if len(ids) < 2:
        return

    # Family cluster from player-known relationships.
    family_ids = [r.npc_id for r in state.relationships if r.kind in ("Mother", "Father", "Sibling")]
    for i in range(len(family_ids)):
        for j in range(i + 1, len(family_ids)):
            _add_edge(state, family_ids[i], family_ids[j], "family", rng.fork(i * 101 + j))
            _add_edge(state, family_ids[j], family_ids[i], "family", rng.fork(i * 101 + j + 1))

    # Everybody gets a few random ties.
    for npc_id in ids:
        others = [x for x in ids if x != npc_id]
        tie_count = min(len(others), 1 + rng.fork(npc_id).randint(0, 3))
        for idx in range(tie_count):
            target = rng.fork(npc_id * 17 + idx).choice(others)
            if any(e.source_id == npc_id and e.target_id == target for e in state.social_edges):
                continue
            rel_type = rng.fork(npc_id * 19 + idx).choice(["friend", "coworker", "enemy"])
            _add_edge(state, npc_id, target, rel_type, rng.fork(npc_id * 23 + idx))


def _neighbors(state: GameState, npc_id: int) -> list[SocialEdge]:
    return [e for e in state.social_edges if e.source_id == npc_id]


def _has_triangle(state: GameState, a: int, b: int, c: int) -> bool:
    return (
        any(e.source_id == a and e.target_id == b for e in state.social_edges)
        and any(e.source_id == b and e.target_id == c for e in state.social_edges)
        and any(e.source_id == c and e.target_id == a for e in state.social_edges)
    )


def _tick_rumours(state: GameState, rng: Rng) -> None:
    new_packets: list[Rumour] = []
    for packet in state.rumours:
        if packet.ttl <= 0 or packet.intensity <= 0.1:
            continue
        hops = _neighbors(state, packet.current_id)
        seen = set(packet.seen_by or [])
        seen.add(packet.current_id)
        for edge in hops:
            if edge.target_id in seen:
                continue
            spread_chance = min(0.95, edge.contact_rate * packet.intensity * (edge.trust / 100))
            if not rng.fork(packet.current_id * 31 + edge.target_id).chance(spread_chance):
                continue
            credibility = max(0.05, packet.credibility - rng.fork(edge.target_id).randint(3, 12) / 100)
            intensity = packet.intensity * 0.75
            new_packets.append(Rumour(
                topic=packet.topic,
                stance=packet.stance,
                origin_id=packet.origin_id,
                current_id=edge.target_id,
                credibility=credibility,
                intensity=intensity,
                ttl=packet.ttl - 1,
                seen_by=list(seen),
            ))
    state.rumours = [r for r in state.rumours if r.ttl > 0 and r.intensity > 0.1]
    state.rumours.extend(new_packets)


def _emit_graph_events(state: GameState, rng: Rng) -> None:
    if state.character is None:
        return
    age = state.character.age
    ids = [a.npc_id for a in state.agents if a.alive]

    # Isolation
    for npc_id in ids:
        deg = len(_neighbors(state, npc_id))
        if deg < 2 and rng.fork(npc_id * 41).chance(0.05):
            state.feed.append(FeedEntry(age=age, text="Someone in your social circle seems increasingly isolated.", kind="bad", entry_id=f"feed:social_isolation:{state.tick}:{npc_id}"))

    # Triangle drama sample (local, probabilistic)
    if len(ids) >= 3 and rng.fork(state.tick).chance(0.15):
        a = rng.fork(1).choice(ids)
        b = rng.fork(2).choice([x for x in ids if x != a])
        c = rng.fork(3).choice([x for x in ids if x not in (a, b)])
        if _has_triangle(state, a, b, c):
            state.feed.append(FeedEntry(age=age, text="A messy social triangle formed among people you know.", kind="bad", entry_id=f"feed:social_triangle:{state.tick}:{a}:{b}:{c}"))

    # Nepotism-like opportunity chain: family -> coworker
    for edge in state.social_edges:
        if edge.relation_type != "family":
            continue
        family_target = edge.target_id
        if any(e.source_id == family_target and e.relation_type == "coworker" for e in state.social_edges):
            if rng.fork(edge.source_id * 7 + edge.target_id).chance(0.04):
                state.feed.append(FeedEntry(age=age, text="A family connection opened a work opportunity in your wider network.", kind="good", entry_id=f"feed:social_nepotism:{state.tick}:{edge.source_id}:{edge.target_id}"))
                break


def tick_social(state: GameState, rng: Rng) -> None:
    if not state.agents:
        return
    if not state.social_edges:
        seed_social_graph(state, rng.fork(5))
    _emit_graph_events(state, rng.fork(11))
    _tick_rumours(state, rng.fork(13))
