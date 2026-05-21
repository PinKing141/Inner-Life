"""GameState — the entire simulated world in one serializable object.

Design rules (matching Fantasy Engine layering):

1. This module has zero I/O, zero Qt imports, zero UI awareness.
2. Mutations happen via core functions, not by callers reaching in.
3. Anything that needs to be saved goes here, full stop.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from core.world import World

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
    first_name: str
    last_name: str
    gender: str
    country: str
    talent: str
    city: str = ""
    age: int = 0
    alive: bool = True
    parents: list[int] = field(default_factory=list)
    children: list[int] = field(default_factory=list)
    lineage_id: str = ""
    birth_story: str = ""
    parent_details: list[dict] = field(default_factory=list)

    @property
    def name(self) -> str:
        """Legacy accessor — most UI surfaces want the full name."""
        if self.last_name:
            return f"{self.first_name} {self.last_name}".strip()
        return self.first_name


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
    university_intent: str = "undecided"  # undecided | attend | skip
    university_major: str = ""  # only meaningful when intent=attend
    university_dropped_out: bool = False
    university_name: str = ""  # generated when the player enrols
    degree_field: str = ""  # broad field of the chosen course (gates degree jobs)
    degree_completed: bool = False  # True once the undergraduate degree is earned
    masters_completed: bool = False
    doctorate_completed: bool = False
    study_years_left: int = 0  # years remaining in the current university program
    scholarship: str = "none"  # none | partial | full (applies to undergrad tuition)
    awaiting_university_choice: bool = False  # UI should prompt the course picker
    degree_award_pending: bool = False  # UI should show the "you graduated" popup
    degree_award_label: str = ""  # e.g. "undergraduate degree", "master's degree"
    # Final school exam (sat at 18) -> grade gates admission and scholarships.
    awaiting_exam: bool = False
    exam_taken: bool = False
    final_school_grade: str = ""
    exam_correct: int = 0
    admitted_tier: str = ""  # Prestigious | Standard | Community | "" (not admitted)


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
    agents: list = field(default_factory=list)  # list[Agent]; typed via core.agents
    social_edges: list = field(default_factory=list)  # list[SocialEdge]; typed via core.social
    rumours: list = field(default_factory=list)  # list[Rumour]; typed via core.social
    career: Job | None = None
    education: Education = field(default_factory=Education)
    feed: list[FeedEntry] = field(default_factory=list)
    pending_event_id: str | None = None  # event awaiting player choice
    fired_events: list[str] = field(default_factory=list)  # ids the player has already seen
    causal_chain: list[dict] = field(default_factory=list)
    world: World = field(default_factory=World)
    tick: int = 0  # how many times age_up has been called
    exam: dict | None = None  # active/finished final school exam (interactive)

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
                    "first_name": self.character.first_name,
                    "last_name": self.character.last_name,
                    "gender": self.character.gender,
                    "country": self.character.country,
                    "city": self.character.city,
                    "talent": self.character.talent,
                    "age": self.character.age,
                    "alive": self.character.alive,
                    "parents": list(self.character.parents),
                    "children": list(self.character.children),
                    "lineage_id": self.character.lineage_id,
                    "birth_story": self.character.birth_story,
                    "parent_details": list(self.character.parent_details),
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
            "agents": [a.to_dict() for a in self.agents],
            "social_edges": [e.to_dict() for e in self.social_edges],
            "rumours": [r.to_dict() for r in self.rumours],
            "causal_chain": list(self.causal_chain),
            "world": self.world.to_dict(),
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
                "university_intent": self.education.university_intent,
                "university_major": self.education.university_major,
                "university_dropped_out": self.education.university_dropped_out,
                "university_name": self.education.university_name,
                "degree_field": self.education.degree_field,
                "degree_completed": self.education.degree_completed,
                "masters_completed": self.education.masters_completed,
                "doctorate_completed": self.education.doctorate_completed,
                "study_years_left": self.education.study_years_left,
                "scholarship": self.education.scholarship,
                "awaiting_university_choice": self.education.awaiting_university_choice,
                "degree_award_pending": self.education.degree_award_pending,
                "degree_award_label": self.education.degree_award_label,
                "awaiting_exam": self.education.awaiting_exam,
                "exam_taken": self.education.exam_taken,
                "final_school_grade": self.education.final_school_grade,
                "exam_correct": self.education.exam_correct,
                "admitted_tier": self.education.admitted_tier,
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
            "fired_events": list(self.fired_events),
            "tick": self.tick,
            "exam": self.exam,
        }


    @classmethod
    def from_dict(cls, data: dict) -> "GameState":
        """Inverse of to_dict. Tolerant to missing fields from older snapshots."""
        from core.agents import Agent  # local import to avoid cycle at module-load
        from core.social import Rumour, SocialEdge

        char_d = data.get("character")
        character: Character | None = None
        if char_d is not None:
            first = char_d.get("first_name")
            last = char_d.get("last_name")
            if first is None and last is None:
                # Legacy snapshot: split a single "name" field.
                full = (char_d.get("name") or "").strip()
                parts = full.split(maxsplit=1)
                first = parts[0] if parts else ""
                last = parts[1] if len(parts) > 1 else ""
            character = Character(
                first_name=first or "",
                last_name=last or "",
                gender=char_d.get("gender", "NonBinary"),
                country=char_d.get("country", ""),
                city=char_d.get("city", ""),
                talent=char_d.get("talent", ""),
                age=char_d.get("age", 0),
                alive=char_d.get("alive", True),
                parents=list(char_d.get("parents", [])),
                children=list(char_d.get("children", [])),
                lineage_id=char_d.get("lineage_id", ""),
                birth_story=char_d.get("birth_story", ""),
                parent_details=list(char_d.get("parent_details", [])),
            )

        stats_d = data.get("stats") or {}
        stats = Stats(
            happiness=stats_d.get("happiness", 100),
            health=stats_d.get("health", 100),
            smarts=stats_d.get("smarts", 50),
            looks=stats_d.get("looks", 50),
        )

        relationships = [
            Relationship(
                npc_id=r["npc_id"],
                name=r["name"],
                kind=r["kind"],
                relationship=r.get("relationship", 50),
                alive=r.get("alive", True),
            )
            for r in data.get("relationships", [])
        ]

        agents = [Agent.from_dict(a) for a in data.get("agents", [])]
        social_edges = [SocialEdge.from_dict(e) for e in data.get("social_edges", [])]
        rumours = [Rumour.from_dict(r) for r in data.get("rumours", [])]

        career_d = data.get("career")
        career = (
            None
            if career_d is None
            else Job(job_id=career_d["job_id"], title=career_d["title"], salary=career_d["salary"])
        )

        edu_d = data.get("education") or {}
        education = Education(
            level=edu_d.get("level", "None"),
            in_school=edu_d.get("in_school", False),
            university_intent=edu_d.get("university_intent", "undecided"),
            university_major=edu_d.get("university_major", ""),
            university_dropped_out=edu_d.get("university_dropped_out", False),
            university_name=edu_d.get("university_name", ""),
            degree_field=edu_d.get("degree_field", ""),
            degree_completed=edu_d.get("degree_completed", False),
            masters_completed=edu_d.get("masters_completed", False),
            doctorate_completed=edu_d.get("doctorate_completed", False),
            study_years_left=edu_d.get("study_years_left", 0),
            scholarship=edu_d.get("scholarship", "none"),
            awaiting_university_choice=edu_d.get("awaiting_university_choice", False),
            degree_award_pending=edu_d.get("degree_award_pending", False),
            degree_award_label=edu_d.get("degree_award_label", ""),
            awaiting_exam=edu_d.get("awaiting_exam", False),
            exam_taken=edu_d.get("exam_taken", False),
            final_school_grade=edu_d.get("final_school_grade", ""),
            exam_correct=edu_d.get("exam_correct", 0),
            admitted_tier=edu_d.get("admitted_tier", ""),
        )

        feed = [
            FeedEntry(
                age=f.get("age", 0),
                text=f.get("text", ""),
                kind=f.get("kind", "neutral"),
                cause_id=f.get("cause_id"),
                entry_id=f.get("entry_id", ""),
            )
            for f in data.get("feed", [])
        ]

        world = World.from_dict(data.get("world") or {})

        return cls(
            seed=data.get("seed", 0),
            mode=data.get("mode", "CREATION"),
            character=character,
            stats=stats,
            money=data.get("money", 0),
            relationships=relationships,
            agents=agents,
            social_edges=social_edges,
            rumours=rumours,
            career=career,
            education=education,
            feed=feed,
            pending_event_id=data.get("pending_event_id"),
            fired_events=list(data.get("fired_events", [])),
            causal_chain=list(data.get("causal_chain", [])),
            world=world,
            tick=data.get("tick", 0),
            exam=data.get("exam"),
        )


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
