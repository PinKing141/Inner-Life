"""Phase 1 — NPC agency.

Every named character (parents, friends, future coworkers) gets an Agent with
their own stats, age, and yearly tick. Their state lives on `GameState.agents`
and the player-facing `Relationship` is a thin view onto an agent.

Design rules:

- Agents tick BEFORE the player's year resolves so "mum died" can feed back
  into player events the same tick.
- All randomness goes through the passed-in Rng so determinism is preserved.
- The player's `Relationship.alive` mirrors the agent's `alive` so the UI
  doesn't need to learn a new shape.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from core.content import names as names_mod
from core import social
from core.rng import Rng
from core.state import FeedEntry, GameState, Relationship


@dataclass
class Agent:
    npc_id: int
    first_name: str
    last_name: str
    gender: str  # "Male" | "Female" | "NonBinary"
    role: str    # Mother, Father, Sibling, Friend, ...
    age: int
    country: str
    city: str = ""
    health: int = 100
    happiness: int = 70
    smarts: int = 50
    looks: int = 50
    generosity: int = 50
    money: int = 0
    job_title: Optional[str] = None
    marital_status: str = "Single"
    education: str = "None"
    alive: bool = True

    @property
    def name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip() or self.first_name

    def to_dict(self) -> dict:
        return {
            "npc_id": self.npc_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "gender": self.gender,
            "role": self.role,
            "age": self.age,
            "country": self.country,
            "city": self.city,
            "health": self.health,
            "happiness": self.happiness,
            "smarts": self.smarts,
            "looks": self.looks,
            "generosity": self.generosity,
            "money": self.money,
            "job_title": self.job_title,
            "marital_status": self.marital_status,
            "education": self.education,
            "alive": self.alive,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Agent":
        return cls(
            npc_id=d["npc_id"],
            first_name=d.get("first_name", d.get("name", "")),
            last_name=d.get("last_name", ""),
            gender=d.get("gender", "NonBinary"),
            role=d.get("role", "Friend"),
            age=d.get("age", 30),
            country=d.get("country", ""),
            city=d.get("city", ""),
            health=d.get("health", 100),
            happiness=d.get("happiness", 70),
            smarts=d.get("smarts", 50),
            looks=d.get("looks", 50),
            generosity=d.get("generosity", 50),
            money=d.get("money", 0),
            job_title=d.get("job_title"),
            marital_status=d.get("marital_status", "Single"),
            education=d.get("education", "None"),
            alive=d.get("alive", True),
        )


# Pools of possible NPC jobs — kept small; the deeper version pulls from
# core.content.jobs but we don't want NPCs to need education/age gating yet.
_NPC_JOBS = [
    "Office Worker", "Nurse", "Teacher", "Driver", "Shop Owner",
    "Engineer", "Accountant", "Cleaner", "Chef", "Electrician",
]


def seed_world(state: GameState, rng: Rng) -> None:
    """Mint Agents for the parents the relationships module already created.

    Keeps player UI unchanged: each Relationship gets a matching Agent record.
    """
    if state.character is None:
        return
    surname = state.character.last_name
    country = state.character.country
    city = state.character.city
    # parent_details (set in sim.new_game) is the single source of truth for a
    # parent's age and job — the birth-story feed reads the same record, so the
    # agent panel must not roll its own conflicting numbers.
    parent_by_role = {d.get("role"): d for d in (state.character.parent_details or [])}

    for rel in state.relationships:
        existing = _find_agent(state, rel.npc_id)
        if existing is not None:
            continue
        if rel.kind == "Mother":
            agent = _new_npc(rel.npc_id, "Female", "Mother", surname, country, city, rng.fork(rel.npc_id), parent_age=True)
        elif rel.kind == "Father":
            agent = _new_npc(rel.npc_id, "Male", "Father", surname, country, city, rng.fork(rel.npc_id + 1), parent_age=True)
        else:
            agent = _new_npc(rel.npc_id, "NonBinary", rel.kind, surname, country, city, rng.fork(rel.npc_id + 2))
        # A parent's age/job come from the birth record, not a fresh roll.
        detail = parent_by_role.get(rel.kind)
        if detail is not None:
            agent.age = detail.get("age_at_birth", agent.age)
            if detail.get("job"):
                agent.job_title = detail["job"]
        # Honour any pre-existing display name on the relationship.
        if rel.name and rel.name not in (agent.first_name, agent.name):
            # Treat the relationship name as the agent's full display name.
            parts = rel.name.strip().split(maxsplit=1)
            agent.first_name = parts[0] if parts else agent.first_name
            agent.last_name = parts[1] if len(parts) > 1 else agent.last_name
        # And refresh the relationship to show the agent's proper name.
        rel.name = agent.name if rel.kind in ("Friend", "Sibling", "Partner", "Coworker") else rel.name
        state.agents.append(agent)

    # --- Phase 2: NPC↔NPC graph ---
    # Wire up the seed edges every life starts with:
    #   * parents are spouses (the canonical NPC↔NPC tie)
    #   * each parent has 1–2 personal friends who DO have their own jobs,
    #     so triangles like "mum's friend offers you a job" can fire later.
    # These extra friend agents are NOT added to state.relationships — the
    # player doesn't know them directly. They surface only through the graph.
    _seed_family_graph(state, rng)


def _seed_family_graph(state: GameState, rng: Rng) -> None:
    mother = next((a for a in state.agents if a.role == "Mother"), None)
    father = next((a for a in state.agents if a.role == "Father"), None)
    if mother is not None and father is not None:
        social.add_edge(state, mother.npc_id, father.npc_id, social.KIND_SPOUSE, strength=90)

    if state.character is None:
        return
    country = state.character.country
    city = state.character.city

    # Counter for fresh NPC ids: keep stepping past anything that already exists
    # (parents, siblings, anything seeded before) so we never collide.
    next_id = max((a.npc_id for a in state.agents), default=0) + 1

    for parent in (mother, father):
        if parent is None:
            continue
        n_friends = 1 + rng.fork(parent.npc_id * 7).randint(0, 1)  # 1 or 2
        for k in range(n_friends):
            f_rng = rng.fork(parent.npc_id * 100 + k)
            gender = f_rng.fork(1).choice(["Male", "Female", "NonBinary"])
            surname = names_mod.random_surname(country, f_rng.fork(2))
            friend = _new_npc(
                next_id, gender, "Family Friend", surname, country, city, f_rng.fork(3),
            )
            # Family friends are adults with jobs — that's the whole point of
            # seeding them; the demo job-referral event needs an employed
            # third party. Clamp to the parent's generation so the friendship
            # is plausible.
            friend.age = max(25, parent.age + f_rng.fork(4).randint(-5, 5))
            if friend.job_title is None:
                friend.job_title = f_rng.fork(5).choice(_NPC_JOBS)
            friend.money = f_rng.fork(6).choice([5_000, 15_000, 30_000, 60_000])
            state.agents.append(friend)
            social.add_edge(state, parent.npc_id, friend.npc_id,
                            social.KIND_FRIEND, strength=f_rng.fork(7).randint(60, 85))
            next_id += 1


def _new_npc(
    npc_id: int,
    gender: str,
    role: str,
    surname: str,
    country: str,
    city: str,
    rng: Rng,
    *,
    parent_age: bool = False,
) -> Agent:
    forename = names_mod.random_forename(country, gender, rng.fork(1))
    if role in ("Mother", "Father"):
        age = 28 + rng.randint(0, 14)
    elif parent_age:
        age = 30 + rng.randint(0, 10)
    elif role == "Sibling":
        age = rng.randint(0, 18)
    else:
        age = 18 + rng.randint(0, 50)
    # Profile flavour. Forked RNG so we don't disturb the draws above.
    if role in ("Mother", "Father"):
        marital = "Married"
    elif age < 18:
        marital = "Single"
    else:
        marital = rng.fork(22).choice(["Single", "Married", "Divorced", "Widowed"])
    if age < 18:
        education = "In school"
    else:
        education = rng.fork(23).choice(["None", "Secondary Education", "University"])

    return Agent(
        npc_id=npc_id,
        first_name=forename,
        last_name=surname,
        gender=gender,
        role=role,
        age=age,
        country=country,
        city=city,
        health=80 + rng.randint(0, 20),
        happiness=50 + rng.randint(0, 40),
        smarts=40 + rng.randint(0, 40),
        looks=40 + rng.randint(0, 40),
        generosity=rng.fork(21).randint(0, 100),
        money=rng.choice([0, 500, 2_000, 5_000, 15_000]),
        job_title=rng.choice(_NPC_JOBS) if age >= 18 else None,
        marital_status=marital,
        education=education,
        alive=True,
    )


def _find_agent(state: GameState, npc_id: int) -> Optional[Agent]:
    for a in state.agents:
        if a.npc_id == npc_id:
            return a
    return None


def _find_relationship(state: GameState, npc_id: int) -> Optional[Relationship]:
    for r in state.relationships:
        if r.npc_id == npc_id:
            return r
    return None


def _kill_agent(state: GameState, agent: Agent, player_age: int) -> None:
    """The single place an agent dies. Flips the agent's `alive`, mirrors it
    onto the player-facing Relationship in the SAME tick, and logs the death.
    Everything that ends an NPC's life should route through here so the agent
    and its relationship can never disagree."""
    agent.alive = False
    rel = _find_relationship(state, agent.npc_id)
    if rel is not None:
        rel.alive = False
    state.feed.append(FeedEntry(
        age=player_age,
        text=f"{agent.name} ({agent.role}) passed away at {agent.age}.",
        kind="bad",
        entry_id=f"feed:agent_death:{state.tick}:{agent.npc_id}",
    ))


def sync_relationship_liveness(state: GameState) -> None:
    """Reconcile every Relationship.alive with its backing Agent.alive.

    `_kill_agent` already keeps the two in step, but this is the invariant's
    hard guarantee: after the world ticks, no relationship can be shown as
    living while its agent is dead — regardless of how the agent died.
    Idempotent and silent (the death feed belongs to whoever did the killing)."""
    by_id = {a.npc_id: a for a in state.agents}
    for rel in state.relationships:
        agent = by_id.get(rel.npc_id)
        if agent is not None and not agent.alive and rel.alive:
            rel.alive = False


def tick_world(state: GameState, rng: Rng) -> None:
    """Run a year for every NPC. May add narrative entries to the feed.

    Called from core.sim.age_up before the player's events roll, so any agent
    state change (death, new job, breakup) is visible to event predicates.
    """
    if state.character is None:
        return
    player_age = state.character.age

    for agent in state.agents:
        if not agent.alive:
            continue

        a_rng = rng.fork(agent.npc_id)
        agent.age += 1

        # Natural drift
        if agent.age > 55:
            agent.health -= a_rng.fork(2).randint(0, 4)
        agent.happiness -= a_rng.fork(3).randint(0, 2)
        if agent.job_title and agent.age >= 18:
            agent.money += max(0, agent.smarts * 50 + a_rng.fork(4).randint(0, 1_500))

        # Job turnover.
        if agent.age >= 18 and a_rng.fork(5).chance(0.05):
            agent.job_title = a_rng.fork(6).choice(_NPC_JOBS)
        # Lose your job (uncommon).
        if agent.job_title and a_rng.fork(7).chance(0.02):
            agent.job_title = None

        # Neglected elders decline faster — a weak player tie now has stakes
        # on the NPC side too, so isolation cuts both ways.
        if agent.age >= 70:
            rel = _find_relationship(state, agent.npc_id)
            if rel is not None and rel.relationship < 30:
                agent.health -= a_rng.fork(8).randint(0, 3)

        # Clamp
        agent.health = max(0, min(100, agent.health))
        agent.happiness = max(0, min(100, agent.happiness))

        # Death check — peaks after 70, plus illness from low health.
        death_chance = max(0.0, (agent.age - 60) * 0.008) + (1 - agent.health / 100) * 0.05
        if agent.health <= 0 or a_rng.fork(11).chance(death_chance):
            _kill_agent(state, agent, player_age)
            continue


# --- Generosity consequence (first vertical slice) ---
# A close, generous relative or friend may bail the player out of debt. This is
# the first place an Agent's `generosity` trait and `money` actually do
# something: until now both were decorative. Connects four previously-isolated
# things — player money, relationship strength, generosity, and agent money.
HELP_MIN_RELATIONSHIP = 60
HELP_MIN_GENEROSITY = 60
HELP_ELIGIBLE_KINDS = ("Mother", "Father", "Sibling", "Partner", "Friend")
# Only steps in for genuine trouble, and not every year — otherwise a single
# rich relative would erase financial failure and hollow out the economy.
HELP_HARDSHIP_BALANCE = -1000  # must be deeper in debt than this
HELP_COOLDOWN_YEARS = 5


def _help_chance(generosity: int, relationship: int) -> float:
    raw = (generosity - 50) / 120 + (relationship - 50) / 200
    return max(0.05, min(0.6, raw))


def offer_financial_help(state: GameState, rng: Rng) -> bool:
    """If the player is in severe debt, a close & generous NPC may give money.

    Gated by a hardship threshold and a cooldown so it can't dominate the
    economy. Picks the most generous eligible helper (deterministic tie-break
    by id), rolls a generosity-weighted chance, then transfers up to half the
    helper's cash to cover the shortfall. Returns True if help was given.
    """
    if state.character is None or state.money >= HELP_HARDSHIP_BALANCE:
        return False
    if state.tick - state.last_help_tick < HELP_COOLDOWN_YEARS:
        return False
    need = -state.money

    candidates: list[tuple[Relationship, Agent]] = []
    for rel in state.relationships:
        if rel.kind not in HELP_ELIGIBLE_KINDS or not rel.alive:
            continue
        if rel.relationship < HELP_MIN_RELATIONSHIP:
            continue
        agent = _find_agent(state, rel.npc_id)
        if agent is None or not agent.alive:
            continue
        if agent.generosity < HELP_MIN_GENEROSITY or agent.money <= 0:
            continue
        candidates.append((rel, agent))
    if not candidates:
        return False
    candidates.sort(key=lambda ra: (-ra[1].generosity, ra[0].npc_id))
    rel, agent = candidates[0]

    if not rng.fork(rel.npc_id).chance(_help_chance(agent.generosity, rel.relationship)):
        return False

    gift = min(need, agent.money // 2)
    if gift <= 0:
        return False

    state.money += gift
    agent.money -= gift
    state.last_help_tick = state.tick
    rel.relationship = min(100, rel.relationship + 5)
    state.stats.happiness = min(100, state.stats.happiness + 5)
    state.feed.append(FeedEntry(
        age=state.character.age,
        text=f"{agent.name} ({agent.role}) saw you were struggling and gave you £{gift:,}.",
        kind="good",
        entry_id=f"feed:help:{state.tick}:{agent.npc_id}",
    ))
    return True


# --- Social renewal (counters graph entropy) ---
# Decay + death only ever shrink the social graph; without formation it trends
# mathematically toward zero. This is the missing counterforce: small, passive,
# context-based weak-tie formation. Deliberately NOT dating/compatibility/AI —
# just enough replenishment to keep the network from self-deleting.
TIE_CAP = 8  # max living weak ties before formation pauses
WEAK_TIE_STRENGTH = (28, 42)  # acquaintances, not close friends


def form_incidental_ties(state: GameState, rng: Rng) -> str | None:
    """Maybe form one weak tie this year, biased by current life context."""
    if state.character is None:
        return None
    age = state.character.age
    if age < 6:
        return None
    living_weak = [
        r for r in state.relationships if r.alive and r.kind in ("Friend", "Coworker")
    ]
    if len(living_weak) >= TIE_CAP:
        return None

    if state.career is not None:
        p, role, descr = 0.18, "Coworker", "a coworker"
    elif state.education.in_school:
        p, role, descr = 0.15, "Friend", "a classmate"
    elif age < 18:
        p, role, descr = 0.12, "Friend", "a friend"
    else:
        p, role, descr = 0.06, "Friend", "someone new"
    # Looks act as social magnetism — a new, money-independent axis. A bounded
    # multiplier (x0.5 .. x1.5), never a gate: everyone can still make ties, the
    # attractive just do so more readily, producing socially-central vs sparse
    # life types orthogonal to wealth.
    p *= 0.5 + state.stats.looks / 100.0
    if not rng.fork(1).chance(p):
        return None

    npc_id = max((a.npc_id for a in state.agents), default=0) + 1
    gender = rng.fork(2).choice(["Male", "Female", "NonBinary"])
    surname = names_mod.random_surname(state.character.country, rng.fork(3))
    agent = _new_npc(npc_id, gender, role, surname, state.character.country, state.character.city, rng.fork(4))
    # Classmates/young friends skew to the player's own age.
    if role == "Friend" and age < 25:
        agent.age = max(5, age + rng.fork(6).randint(-2, 2))
    state.agents.append(agent)
    state.relationships.append(Relationship(
        npc_id=npc_id, name=agent.name, kind=role,
        relationship=rng.fork(5).randint(*WEAK_TIE_STRENGTH), alive=True,
    ))
    # Phase 2: a new friend doesn't appear in a vacuum — they typically have
    # at least one tie to someone already in the world. Picking from existing
    # agents (not the player) progressively densifies the graph and lets
    # triangles form across the years.
    _link_into_graph(state, agent.npc_id, rng.fork(8))
    return f"You became friendly with {agent.name}, {descr}."


def _link_into_graph(state: GameState, npc_id: int, rng: Rng) -> None:
    """Optionally add one NPC↔NPC friendship from ``npc_id`` to another
    living agent already in the world. Deterministic given ``rng``."""
    candidates = [
        a.npc_id for a in state.agents
        if a.alive and a.npc_id != npc_id and a.role != "Mother" and a.role != "Father"
    ]
    if not candidates:
        return
    # ~40% of the time form a new tie — rare enough not to flood the graph,
    # frequent enough to seed triangles over a few decades.
    if not rng.fork(1).chance(0.4):
        return
    other = rng.fork(2).choice(candidates)
    social.add_edge(state, npc_id, other,
                    social.KIND_FRIEND, strength=rng.fork(3).randint(35, 65))


# --- Partner formation (producer for an already-consumed edge type) ---
# `Partner` is consumed by support (CLOSE_KINDS) and generosity
# (HELP_ELIGIBLE_KINDS) but nothing ever produced one. This closes that loop.
# Partnerships are produced by deepening an existing strong tie — so socially
# active / attractive people pair up and the isolated rarely do — and they
# PERSIST (exempt from decay in relationships.annual_drift), ending only via a
# small annual breakup chance or the partner's death.
PARTNER_MIN_AGE = 18
PARTNER_TIE_THRESHOLD = 40
PARTNER_FORM_STRENGTH = (70, 85)
PARTNER_BREAKUP_CHANCE = 0.04


def tick_partner(state: GameState, rng: Rng) -> str | None:
    if state.character is None or state.character.age < PARTNER_MIN_AGE:
        return None
    # Love/Dating v1: when the player is actively pursuing someone, the
    # random partner pathway steps aside so a surprise NPC pairing doesn't
    # displace their prospect. Partner breakup still rolls — the player
    # might lose a long-term partner regardless of any new dating arc.
    if state.dating is not None:
        return None
    partner = next((r for r in state.relationships if r.kind == "Partner" and r.alive), None)
    if partner is not None:
        if rng.fork(1).chance(PARTNER_BREAKUP_CHANCE):
            state.relationships = [r for r in state.relationships if r is not partner]
            return f"You and {partner.name} broke up."
        return None

    looks_factor = 0.5 + state.stats.looks / 100.0
    strong_ties = [
        r for r in state.relationships
        if r.alive and r.kind in ("Friend", "Coworker") and r.relationship >= PARTNER_TIE_THRESHOLD
    ]
    if strong_ties:
        strong_ties.sort(key=lambda r: (-r.relationship, r.npc_id))
        if rng.fork(2).chance(0.12 * looks_factor):
            tie = strong_ties[0]
            tie.kind = "Partner"
            tie.relationship = rng.fork(3).randint(*PARTNER_FORM_STRENGTH)
            agent = _find_agent(state, tie.npc_id)
            if agent is not None:
                agent.role = "Partner"  # keep agent/relationship truth aligned
            return f"You and {tie.name} became a couple."
        return None

    # No close ties to deepen — small chance to meet someone new instead.
    if rng.fork(4).chance(0.03 * looks_factor):
        npc_id = max((a.npc_id for a in state.agents), default=0) + 1
        gender = rng.fork(5).choice(["Male", "Female", "NonBinary"])
        surname = names_mod.random_surname(state.character.country, rng.fork(6))
        agent = _new_npc(npc_id, gender, "Partner", surname, state.character.country, state.character.city, rng.fork(7))
        agent.age = max(18, state.character.age + rng.fork(8).randint(-5, 5))
        state.agents.append(agent)
        state.relationships.append(Relationship(
            npc_id=npc_id, name=agent.name, kind="Partner",
            relationship=rng.fork(9).randint(*PARTNER_FORM_STRENGTH), alive=True,
        ))
        return f"You met {agent.name} and became a couple."
    return None


def add_friend(state: GameState, rng: Rng, role: str = "Friend") -> Agent:
    """Mint a new friend agent the player just made and wire up the relationship."""
    if state.character is None:
        raise ValueError("No character yet")
    npc_id = max((a.npc_id for a in state.agents), default=0) + 1
    gender = rng.choice(["Male", "Female", "NonBinary"])
    surname = names_mod.random_surname(state.character.country, rng.fork(1))
    agent = _new_npc(npc_id, gender, role, surname, state.character.country, state.character.city, rng.fork(2))
    state.agents.append(agent)
    state.relationships.append(Relationship(
        npc_id=npc_id, name=agent.name, kind=role, relationship=60, alive=True,
    ))
    return agent
