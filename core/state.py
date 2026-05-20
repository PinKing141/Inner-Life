"""GameState — the entire simulated world in one serializable object.

Design rules (matching Fantasy Engine layering):

1. This module has zero I/O, zero Qt imports, zero UI awareness.
2. Mutations happen via core functions, not by callers reaching in.
3. Anything that needs to be saved goes here, full stop.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Stage = Literal["Baby", "Child", "Teenager", "Adult", "Elder"]
GameMode = Literal["CREATION", "PLAYING", "DEATH"]


@dataclass
class Stats:
    happiness: int = 100
    health: int = 100
    smarts: int = 50
    looks: int = 50

    def clamped(self) -> "Stats":
        return Stats(
            happiness=max(0, min(100, self.happiness)),
            health=max(0, min(100, self.health)),
            smarts=max(0, min(100, self.smarts)),
            looks=max(0, min(100, self.looks)),
        )

    def to_dict(self) -> dict:
        return {
            "happiness": self.happiness,
            "health": self.health,
            "smarts": self.smarts,
            "looks": self.looks,
        }


@dataclass
class Character:
    name: str
    gender: str
    country: str
    talent: str
    age: int = 0
    alive: bool = True


@dataclass
class Relationship:
    """A node in the player's social graph.

    `relationship` is 0-100. NPC traits/goals would go here in a deeper pass
    (currently just enough to make the UI work; see roadmap in README).
    """

    npc_id: int
    name: str
    kind: str  # Mother, Father, Sibling, Friend, Partner, Coworker, ...
    relationship: int = 50
    alive: bool = True


@dataclass
class Job:
    job_id: str
    title: str
    salary: int


@dataclass
class Education:
    level: str = "None"
    in_school: bool = False


@dataclass
class FeedEntry:
    """A line in the life log. Tagged with the causal chain (if any) so the
    narrative reader can later surface 'X happened because Y'."""

    age: int
    text: str
    kind: str  # neutral | good | bad | special
    cause_id: str | None = None  # foreign key into causal_chain
    entry_id: str = ""


@dataclass
class GameState:
    """The complete simulated world."""

    seed: int
    mode: GameMode = "CREATION"
    character: Character | None = None
    stats: Stats = field(default_factory=Stats)
    money: int = 0
    relationships: list[Relationship] = field(default_factory=list)
    career: Job | None = None
    education: Education = field(default_factory=Education)
    feed: list[FeedEntry] = field(default_factory=list)
    pending_event_id: str | None = None  # event awaiting player choice
    fired_event_ids: list[str] = field(default_factory=list)  # events already shown to the player
    causal_chain: list[dict] = field(default_factory=list)
    tick: int = 0  # how many times age_up has been called

    # --- Serialization (for save/load and JS bridge) ---

    def to_dict(self) -> dict:
        return {
            "seed": self.seed,
            "mode": self.mode,
            "character": (
                None
                if self.character is None
                else {
                    "name": self.character.name,
                    "gender": self.character.gender,
                    "country": self.character.country,
                    "talent": self.character.talent,
                    "age": self.character.age,
                    "alive": self.character.alive,
                }
            ),
            "stats": self.stats.to_dict(),
            "money": self.money,
            "relationships": [
                {
                    "npc_id": r.npc_id,
                    "name": r.name,
                    "kind": r.kind,
                    "relationship": r.relationship,
                    "alive": r.alive,
                }
                for r in self.relationships
            ],
            "career": (
                None
                if self.career is None
                else {
                    "job_id": self.career.job_id,
                    "title": self.career.title,
                    "salary": self.career.salary,
                }
            ),
            "education": {
                "level": self.education.level,
                "in_school": self.education.in_school,
            },
            "feed": [
                {
                    "age": f.age,
                    "text": f.text,
                    "kind": f.kind,
                    "cause_id": f.cause_id,
                    "entry_id": f.entry_id,
                }
                for f in self.feed
            ],
            "pending_event_id": self.pending_event_id,
            "fired_event_ids": list(self.fired_event_ids),
            "tick": self.tick,
        }


def stage_for_age(age: int) -> Stage:
    if age < 5:
        return "Baby"
    if age < 13:
        return "Child"
    if age < 18:
        return "Teenager"
    if age < 65:
        return "Adult"
    return "Elder"
