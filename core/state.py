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
    employer: str = ""
    career: str = ""  # the profession (Title may gain a rank prefix on promotion)
    level: int = 0  # promotion rank, 0 = entry
    performance: int = 50  # 0-100, raised by working harder, drives promotions
    last_ask_tick: int = -1  # tick of the player's last raise/promotion request


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
class PregnancyState:
    """Phase 6 — Pregnancy v1.

    Tracks an in-progress gestation. Resolution happens one tick after
    conception in ``sim.age_up`` -> ``genealogy.resolve_pregnancy``, so the
    birth event always lands on the year after the player chose to try.

    ``carrier_is_player`` matters for future maternity-leave / health
    events (queued for v2). In v1 both code paths land in the same
    ``pending_birth`` modal, but the field lets later events gate cleanly.

    Partner stats are snapshotted at conception so the child's inherited
    looks/smarts don't shift if the partner trains or ages between
    conception and birth.
    """
    is_active: bool = False
    carrier_is_player: bool = True
    partner_npc_id: int | None = None
    conception_age: int = 0
    conception_tick: int = 0
    partner_looks: int = 50   # snapshot for genetic blend
    partner_smarts: int = 50  # snapshot for genetic blend
    partner_name: str = ""    # for narrative consistency if partner agent vanishes


@dataclass
class CriminalRecord:
    """Phase 6 — Crime v1.

    Tracks active incarceration and a permanent history of convictions.
    The boolean ``is_incarcerated`` overrides the standard life loop in
    ``sim.age_up``; ``past_offences`` survives release so predicates
    like ``HasCriminalRecord`` can gate prestigious jobs and certain
    events forever.

    ``sentence_years`` and ``years_served`` are both annual counters; on
    each prison tick ``years_served`` is incremented and when it reaches
    ``sentence_years`` the player walks out (sim.age_up handles the
    release transition, not this dataclass).
    """
    is_incarcerated: bool = False
    sentence_years: int = 0
    years_served: int = 0
    past_offences: list[str] = field(default_factory=list)


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
    career: Job | None = None
    education: Education = field(default_factory=Education)
    feed: list[FeedEntry] = field(default_factory=list)
    pending_event_id: str | None = None  # event awaiting player choice
    fired_events: list[str] = field(default_factory=list)  # ids the player has already seen
    causal_chain: list[dict] = field(default_factory=list)
    world: World = field(default_factory=World)
    tick: int = 0  # how many times age_up has been called
    last_help_tick: int = -100  # tick of the last NPC financial bailout (cooldown)
    exam: dict | None = None  # active/finished final school exam (interactive)
    pending_job_offer: dict | None = None  # "you got the job" popup
    pending_promotion: dict | None = None  # "you got promoted" popup
    pending_job_loss: dict | None = None  # "you were laid off / fired" popup
    pending_career_setback: dict | None = None  # demotion / pay-cut popup
    job_application_error: str | None = None  # last rejected application message
    properties: list = field(default_factory=list)  # owned homes [{id,name,value,purchase_price}]
    rental: dict | None = None  # current rental {id,name,rent}
    # Phase 6 — Cars/Assets v1. Owned vehicles; each is a dict with
    # instance_id, car_id, current_value, age_years, depreciation_rate.
    # See core.cars for the catalogue and verbs.
    vehicles: list = field(default_factory=list)
    # Phase 5 — genealogy. `ancestors` is the archive of prior playable
    # characters: when the player dies and continues as a child, the
    # outgoing life is snapshotted here so legend / family-history UI can
    # read it back. Each entry is a dict (see core.genealogy.snapshot).
    ancestors: list[dict] = field(default_factory=list)
    social_edges: list = field(default_factory=list)  # list[SocialEdge]; typed via core.social
    # Phase 6 — Pregnancy v1. An active gestation registered by either
    # the consider_child event (guaranteed) or attempt_conception
    # (probabilistic, e.g. broken_condom event). Resolves one tick later
    # in sim.age_up via genealogy.resolve_pregnancy.
    pregnancy: PregnancyState = field(default_factory=PregnancyState)
    # When a pregnancy resolves successfully, the naming modal payload
    # lives here until the player picks a name. Shape: {npc_id, gender,
    # suggested_name, last_name}. The UI raises a modal with a text input.
    pending_birth: dict | None = None
    # Phase 6 — Love/Dating v1. Current dating prospect (None when single
    # or already committed). Shape: {npc_id, name, age, gender, chemistry,
    # dates_been_on, started_tick}. The same NPC also lives as a
    # Relationship with kind="Dating"; the dict is a fast accessor so
    # event predicates / UI panels don't have to scan relationships.
    # On commitment (become_official), the Relationship flips to
    # kind="Partner" and this field clears.
    dating: dict | None = None
    # Milestone popups for life moments (turning 18, 30, 50, 65, 100). Set
    # by sim.age_up when the player crosses a threshold; the UI raises a
    # modal and the bridge clears it via acknowledgeMilestone. Shape:
    # {"id": "milestone:18", "age": 18, "title": "...", "subtitle": "..."}
    pending_milestone: dict | None = None
    # Ages at which a milestone has already fired (so post-load + heir
    # transitions don't re-trigger them on the same character).
    milestones_seen: list[int] = field(default_factory=list)
    # Phase 6 — Crime v1. Tracks active incarceration + past convictions.
    # While `crime.is_incarcerated` is true, sim.age_up runs a prison
    # tick (no career/education/economy) and the event engine restricts
    # candidates to IsIncarcerated-gated events.
    crime: CriminalRecord = field(default_factory=CriminalRecord)
    # Outcome modal payload set by crime.attempt_crime ({title, text,
    # caught, payout}). UI raises a modal; verb acknowledge_crime_outcome
    # clears it.
    pending_crime_outcome: dict | None = None

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
            "causal_chain": list(self.causal_chain),
            "world": self.world.to_dict(),
            "career": (
                None
                if self.career is None
                else {
                    "job_id": self.career.job_id,
                    "title": self.career.title,
                    "salary": self.career.salary,
                    "employer": self.career.employer,
                    "career": self.career.career,
                    "level": self.career.level,
                    "performance": self.career.performance,
                    "last_ask_tick": self.career.last_ask_tick,
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
            "last_help_tick": self.last_help_tick,
            "exam": self.exam,
            "pending_job_offer": self.pending_job_offer,
            "pending_promotion": self.pending_promotion,
            "pending_job_loss": self.pending_job_loss,
            "pending_career_setback": self.pending_career_setback,
            "job_application_error": self.job_application_error,
            "properties": list(self.properties),
            "vehicles": list(self.vehicles),
            "rental": self.rental,
            "ancestors": list(self.ancestors),
            "social_edges": [e.to_dict() for e in self.social_edges],
            "pregnancy": {
                "is_active": self.pregnancy.is_active,
                "carrier_is_player": self.pregnancy.carrier_is_player,
                "partner_npc_id": self.pregnancy.partner_npc_id,
                "conception_age": self.pregnancy.conception_age,
                "conception_tick": self.pregnancy.conception_tick,
                "partner_looks": self.pregnancy.partner_looks,
                "partner_smarts": self.pregnancy.partner_smarts,
                "partner_name": self.pregnancy.partner_name,
            },
            "pending_birth": self.pending_birth,
            "dating": self.dating,
            "pending_milestone": self.pending_milestone,
            "milestones_seen": list(self.milestones_seen),
            "crime": {
                "is_incarcerated": self.crime.is_incarcerated,
                "sentence_years": self.crime.sentence_years,
                "years_served": self.crime.years_served,
                "past_offences": list(self.crime.past_offences),
            },
            "pending_crime_outcome": self.pending_crime_outcome,
        }


    @classmethod
    def from_dict(cls, data: dict) -> "GameState":
        """Inverse of to_dict. Tolerant to missing fields from older snapshots."""
        from core.agents import Agent  # local import to avoid cycle at module-load
        from core.social import SocialEdge  # ditto

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

        career_d = data.get("career")
        career = (
            None
            if career_d is None
            else Job(
                job_id=career_d["job_id"],
                title=career_d["title"],
                salary=career_d["salary"],
                employer=career_d.get("employer", ""),
                career=career_d.get("career", ""),
                level=career_d.get("level", 0),
                performance=career_d.get("performance", 50),
                last_ask_tick=career_d.get("last_ask_tick", -1),
            )
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
            career=career,
            education=education,
            feed=feed,
            pending_event_id=data.get("pending_event_id"),
            fired_events=list(data.get("fired_events", [])),
            last_help_tick=data.get("last_help_tick", -100),
            causal_chain=list(data.get("causal_chain", [])),
            world=world,
            tick=data.get("tick", 0),
            exam=data.get("exam"),
            pending_job_offer=data.get("pending_job_offer"),
            pending_promotion=data.get("pending_promotion"),
            pending_job_loss=data.get("pending_job_loss"),
            pending_career_setback=data.get("pending_career_setback"),
            job_application_error=data.get("job_application_error"),
            properties=list(data.get("properties", [])),
            vehicles=list(data.get("vehicles", [])),
            rental=data.get("rental"),
            ancestors=list(data.get("ancestors", [])),
            social_edges=[SocialEdge.from_dict(e) for e in data.get("social_edges", [])],
            pregnancy=(
                PregnancyState(**data["pregnancy"])
                if isinstance(data.get("pregnancy"), dict)
                else PregnancyState()
            ),
            pending_birth=data.get("pending_birth"),
            dating=data.get("dating"),
            pending_milestone=data.get("pending_milestone"),
            milestones_seen=list(data.get("milestones_seen", [])),
            crime=(
                CriminalRecord(**data["crime"])
                if isinstance(data.get("crime"), dict)
                else CriminalRecord()
            ),
            pending_crime_outcome=data.get("pending_crime_outcome"),
        )
