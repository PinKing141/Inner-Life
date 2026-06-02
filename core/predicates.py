"""Tiny predicate DSL for state-gated events (Phase 6).

Each predicate is a callable ``(GameState) -> bool``. Events in
`core.content.events` may include a `predicates` list; the event engine
filters out events whose predicates aren't all satisfied BEFORE rolling
probability, so careers/wealth/stats actually shape what happens.

Keep these declarative: predicates must not mutate state.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from core.state import GameState

Predicate = Callable[[GameState], bool]


# --- Core combinators ------------------------------------------------------

def AND(*preds: Predicate) -> Predicate:
    def inner(s: GameState) -> bool:
        return all(p(s) for p in preds)
    return inner


def OR(*preds: Predicate) -> Predicate:
    def inner(s: GameState) -> bool:
        return any(p(s) for p in preds)
    return inner


def NOT(p: Predicate) -> Predicate:
    return lambda s: not p(s)


# --- Stat / money / state predicates --------------------------------------

@dataclass(frozen=True)
class MinStat:
    """Requires state.stats.<stat> >= value."""
    stat: str
    value: int

    def __call__(self, s: GameState) -> bool:
        return getattr(s.stats, self.stat, 0) >= self.value


@dataclass(frozen=True)
class MaxStat:
    stat: str
    value: int

    def __call__(self, s: GameState) -> bool:
        return getattr(s.stats, self.stat, 0) <= self.value


def MinSmarts(v: int) -> Predicate:
    return MinStat("smarts", v)


def MinHealth(v: int) -> Predicate:
    return MinStat("health", v)


def MinHappiness(v: int) -> Predicate:
    return MinStat("happiness", v)


def MinLooks(v: int) -> Predicate:
    return MinStat("looks", v)


@dataclass(frozen=True)
class MinMoney:
    value: int

    def __call__(self, s: GameState) -> bool:
        return s.money >= self.value


@dataclass(frozen=True)
class MaxMoney:
    value: int

    def __call__(self, s: GameState) -> bool:
        return s.money <= self.value


@dataclass(frozen=True)
class InDebt:
    def __call__(self, s: GameState) -> bool:
        return s.money < 0


# --- Career / education ---------------------------------------------------


@dataclass(frozen=True)
class DuringRecession:
    def __call__(self, s: GameState) -> bool:
        return s.world.recession


@dataclass(frozen=True)
class DuringWar:
    def __call__(self, s: GameState) -> bool:
        return s.world.war


@dataclass(frozen=True)
class MinInflationIndex:
    value: float

    def __call__(self, s: GameState) -> bool:
        return s.world.inflation_index >= self.value


@dataclass(frozen=True)
class HasJob:
    """True if the player has any job."""

    def __call__(self, s: GameState) -> bool:
        return s.career is not None


@dataclass(frozen=True)
class NoJob:
    def __call__(self, s: GameState) -> bool:
        return s.career is None


@dataclass(frozen=True)
class JobIs:
    """Match by job_id (e.g. ``JobIs("doctor")``)."""
    job_id: str

    def __call__(self, s: GameState) -> bool:
        return s.career is not None and s.career.job_id == self.job_id


@dataclass(frozen=True)
class JobInAny:
    job_ids: tuple[str, ...]

    def __call__(self, s: GameState) -> bool:
        return s.career is not None and s.career.job_id in self.job_ids


# Convenience constructor.
def RequiresJob(job_id: str) -> Predicate:
    return JobIs(job_id)


@dataclass(frozen=True)
class EducationAtLeast:
    """Match if education level >= the given level (string key)."""
    level: str

    def __call__(self, s: GameState) -> bool:
        # Import inside to keep this module dependency-light.
        from core.content.jobs import education_meets
        return education_meets(s.education.level, self.level)


@dataclass(frozen=True)
class InSchool:
    def __call__(self, s: GameState) -> bool:
        return s.education.in_school


# --- Demographics ---------------------------------------------------------

@dataclass(frozen=True)
class CountryIs:
    country: str  # display name or ISO-2

    def __call__(self, s: GameState) -> bool:
        if not s.character:
            return False
        from core.content.countries import resolve
        return resolve(self.country).code == resolve(s.character.country).code


@dataclass(frozen=True)
class GenderIs:
    gender: str

    def __call__(self, s: GameState) -> bool:
        return s.character is not None and s.character.gender == self.gender


# --- Relationships / agents -----------------------------------------------

@dataclass(frozen=True)
class HasLivingRelationship:
    kind: str

    def __call__(self, s: GameState) -> bool:
        return any(r.kind == self.kind and r.alive for r in s.relationships)


@dataclass(frozen=True)
class HasNoLivingRelationship:
    kind: str

    def __call__(self, s: GameState) -> bool:
        return not any(r.kind == self.kind and r.alive for r in s.relationships)


# --- Phase 5: genealogy -----------------------------------------------------


@dataclass(frozen=True)
class ChildCountAtMost:
    """True when the player's existing children list is at or below ``n``.
    Lets the 'consider a child?' event taper off naturally as a family
    grows, rather than firing indefinitely."""

    n: int

    def __call__(self, s: GameState) -> bool:
        if s.character is None:
            return False
        return len(s.character.children) <= self.n


@dataclass(frozen=True)
class HasLivingChild:
    """True when the player has at least one living child Agent — the
    minimum condition for the 'continue as heir' transition to be offered
    on death."""

    def __call__(self, s: GameState) -> bool:
        if s.character is None:
            return False
        child_ids = set(s.character.children)
        return any(a.alive for a in s.agents if a.npc_id in child_ids)


# --- Phase 6: Pregnancy v1 -------------------------------------------------


@dataclass(frozen=True)
class IsPregnant:
    """True while the player has an active gestation. Used to gate
    pregnancy-only events (morning sickness, maternity-leave question)."""

    def __call__(self, s: GameState) -> bool:
        return s.pregnancy.is_active


# --- Crime v1 ---------------------------------------------------------------


@dataclass(frozen=True)
class IsIncarcerated:
    """True while the player is doing time. Used to flag events that
    should ONLY fire in prison (yard fight, parole hearing) and to
    short-circuit the event roll otherwise."""

    def __call__(self, s: GameState) -> bool:
        return s.crime.is_incarcerated


@dataclass(frozen=True)
class HasCriminalRecord:
    """True if the player has any past conviction, even after release.
    Use to gate prestigious-job events, distrust drama, parole-officer
    visits etc. that should react to the player's permanent record."""

    def __call__(self, s: GameState) -> bool:
        return len(s.crime.past_offences) > 0


# --- Cars / Assets v1 -----------------------------------------------------


@dataclass(frozen=True)
class OwnsAVehicle:
    """True when the player owns at least one car. Used to gate
    car-related drama events (breakdown, theft, road trip)."""

    def __call__(self, s: GameState) -> bool:
        return len(s.vehicles) > 0


# --- Phase 2: graph-shape predicates --------------------------------------


@dataclass(frozen=True)
class RelativeHasEmployedFriend:
    """True if the player has a living relative of the given kind whose
    NPC↔NPC social graph contains at least one living, employed friend.

    This is the first event predicate that reads from the Phase 2 social
    graph rather than the player's direct relationships — it powers things
    like 'your mother's friend has a job for you' that wouldn't be possible
    with a star-graph centred on the player."""

    relative_kind: str

    def __call__(self, s: GameState) -> bool:
        from core import social
        agent_by_id = {a.npc_id: a for a in s.agents}
        for r in s.relationships:
            if r.kind != self.relative_kind or not r.alive:
                continue
            for nb_id in social.neighbors(s, r.npc_id, kind=social.KIND_FRIEND):
                friend = agent_by_id.get(nb_id)
                if friend is not None and friend.alive and friend.job_title:
                    return True
        return False


# --- Love/Dating v1 -------------------------------------------------------


@dataclass(frozen=True)
class IsDating:
    """True when the player has a current dating prospect (pre-commitment).
    Used to gate dating-arc drama events (met-their-friends, jealousy, …).
    """

    def __call__(self, s: GameState) -> bool:
        return s.dating is not None


@dataclass(frozen=True)
class IsSingle:
    """True when the player has neither a Partner nor a dating prospect.
    Gates events that only make sense for the romantically unattached."""

    def __call__(self, s: GameState) -> bool:
        if s.dating is not None:
            return False
        return not any(r.kind == "Partner" and r.alive for r in s.relationships)


@dataclass(frozen=True)
class MinChemistry:
    """Player's dating chemistry is at or above the given threshold.
    False when not dating at all — chemistry only exists with a prospect."""

    value: int

    def __call__(self, s: GameState) -> bool:
        if s.dating is None:
            return False
        return s.dating.get("chemistry", 0) >= self.value


# --- Evaluation -----------------------------------------------------------

def evaluate(preds: list[Predicate] | None, state: GameState) -> bool:
    """All predicates must pass. An empty/None list is treated as ``True``."""
    if not preds:
        return True
    return all(p(state) for p in preds)
