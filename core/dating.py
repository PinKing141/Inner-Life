"""Love/Dating v1 — player-driven romance loop.

Before this module, romance was passive: ``agents.tick_partner`` rolled
random partner formation each year and the player could only watch. v1
adds agency: the player asks someone out, takes them on dates, and
either commits or walks away.

State machine
-------------

::

    single ──ask_someone_out──▶ dating ──become_official──▶ partnered
       ▲                          │                              │
       └───────break_up───────────┘                              │
       └────────────────────────break_up─────────────────────────┘

Where state lives
-----------------

- ``state.dating`` (``dict | None``) is the fast accessor for the current
  prospect — what events and UI read to gate themselves. Keys:
  ``npc_id``, ``name``, ``age``, ``gender``, ``chemistry`` (0-100),
  ``dates_been_on`` (int), ``started_tick`` (int).
- The same NPC is stored as an Agent (``role="Dating"``) and a player
  Relationship (``kind="Dating"``) so the Relations screen lists them
  next to everyone else, and the existing player-side modules don't need
  to learn a new shape.
- On commitment, the Relationship.kind flips to ``"Partner"`` and the
  Agent.role flips to ``"Partner"``. ``state.dating`` clears. From this
  point forward the rest of the sim (partner breakup, consider_child,
  date_night, eligible_heirs) handles them as a normal Partner.

Coexistence with tick_partner
-----------------------------

``agents.tick_partner`` keeps working for inactive players (no dating,
no partner). When ``state.dating`` is set, the random partner pathway
short-circuits so the player's prospect isn't displaced by a surprise
NPC pairing. See ``has_active_romance``.

Determinism
-----------

All randomness goes through a forked Rng (callers pass one in). Same
seed + same sequence of player verbs → same outcomes, life after life.
"""
from __future__ import annotations

from typing import Optional

from core.content import names as names_mod
from core.rng import Rng
from core.state import GameState, Relationship


MIN_DATING_AGE = 16
DATE_COST = 50
COMMIT_CHEMISTRY_THRESHOLD = 60
MAX_CHEMISTRY = 100


# --- Helpers ---------------------------------------------------------------


def _next_npc_id(state: GameState) -> int:
    """Find a free npc_id that doesn't collide with any Agent or Relationship.
    Same convention as core.genealogy._next_npc_id."""
    max_agent = max((a.npc_id for a in state.agents), default=0)
    max_rel = max((r.npc_id for r in state.relationships), default=0)
    return max(max_agent, max_rel) + 1


def _find_agent(state: GameState, npc_id: int):
    for a in state.agents:
        if a.npc_id == npc_id:
            return a
    return None


def _find_dating_relationship(state: GameState) -> Optional[Relationship]:
    """The Dating relationship that mirrors state.dating, if any."""
    if state.dating is None:
        return None
    npc_id = state.dating.get("npc_id")
    return next((r for r in state.relationships if r.npc_id == npc_id), None)


def _find_partner_relationship(state: GameState) -> Optional[Relationship]:
    return next(
        (r for r in state.relationships if r.kind == "Partner" and r.alive),
        None,
    )


def has_active_romance(state: GameState) -> bool:
    """True if the player has either a dating prospect or a Partner.
    Used by tick_partner to avoid trampling player-led romance."""
    return state.dating is not None or _find_partner_relationship(state) is not None


# --- Verbs -----------------------------------------------------------------


def ask_someone_out(state: GameState, rng: Rng) -> tuple[bool, str]:
    """Mint a date prospect and start the dating arc.

    Returns ``(ok, log)``. Refuses (False) when the player is too young,
    already has a Partner, is already dating someone, or is dead.
    """
    if state.character is None or not state.character.alive:
        return False, "You can't date right now."
    if state.character.age < MIN_DATING_AGE:
        return False, "You're too young to be asking people out."
    if state.dating is not None:
        return False, f"You're already seeing {state.dating['name']}."
    if _find_partner_relationship(state) is not None:
        return False, "You're already in a committed relationship."

    # Mint a prospect Agent. Light personality biased to be a believable
    # match: age ±4 of player, looks midrange-up.
    from core.agents import Agent  # local to dodge import cycle

    surname = names_mod.random_surname(state.character.country, rng.fork(1))
    gender = rng.fork(2).choice(["Male", "Female", "NonBinary"])
    forename = names_mod.random_forename(state.character.country, gender, rng.fork(3))
    age = max(MIN_DATING_AGE, state.character.age + rng.fork(4).randint(-4, 4))
    npc_id = _next_npc_id(state)

    prospect = Agent(
        npc_id=npc_id,
        first_name=forename,
        last_name=surname,
        gender=gender,
        role="Dating",
        age=age,
        country=state.character.country,
        city=state.character.city,
        health=70 + rng.fork(5).randint(0, 30),
        happiness=60 + rng.fork(6).randint(0, 30),
        smarts=40 + rng.fork(7).randint(0, 40),
        looks=50 + rng.fork(8).randint(0, 40),
        generosity=rng.fork(9).randint(20, 80),
        money=rng.choice([0, 1_000, 5_000, 15_000]),
        job_title=None,
        marital_status="Single",
        education="None",
        alive=True,
    )
    state.agents.append(prospect)
    state.relationships.append(Relationship(
        npc_id=npc_id, name=prospect.name, kind="Dating",
        relationship=50, alive=True,
    ))
    # Initial chemistry rolls 25-45 — there's a spark, but commitment
    # needs at least one good date or two (chemistry >= 60 to commit).
    initial_chemistry = 25 + rng.fork(10).randint(0, 20)
    state.dating = {
        "npc_id": npc_id,
        "name": prospect.name,
        "age": prospect.age,
        "gender": prospect.gender,
        "chemistry": initial_chemistry,
        "dates_been_on": 0,
        "started_tick": state.tick,
    }
    return True, f"You asked {prospect.name} out. They said yes."


def go_on_date(state: GameState, rng: Rng) -> tuple[bool, str]:
    """Spend money on a date. Chemistry rises by a noisy amount biased by
    the player's looks. Caps at MAX_CHEMISTRY.

    Refuses without an active prospect or when the player can't afford
    the date.
    """
    if state.dating is None:
        return False, "You're not dating anyone right now."
    if state.money < DATE_COST:
        return False, f"You can't afford a £{DATE_COST} date this week."

    state.money -= DATE_COST
    # Chemistry gain ranges roughly 3-12 with a looks-tilt. Bad-luck rolls
    # can still happen so dating isn't a frictionless ladder.
    looks_factor = 0.7 + state.stats.looks / 200.0  # 0.7-1.2
    base = rng.fork(11).randint(3, 12)
    gain = max(1, int(base * looks_factor))
    state.dating["chemistry"] = min(MAX_CHEMISTRY, state.dating["chemistry"] + gain)
    state.dating["dates_been_on"] += 1

    # Mirror onto the Relationship so the Relations screen feels alive too.
    rel = _find_dating_relationship(state)
    if rel is not None:
        rel.relationship = min(100, rel.relationship + max(1, gain // 2))

    name = state.dating["name"]
    chem = state.dating["chemistry"]
    if chem >= COMMIT_CHEMISTRY_THRESHOLD:
        suffix = " You're starting to think this might be it."
    elif gain <= 3:
        suffix = " It was nice, if a little quiet."
    else:
        suffix = " It went really well."
    return True, f"You and {name} spent an evening together.{suffix} £{DATE_COST}."


def become_official(state: GameState) -> tuple[bool, str]:
    """Promote the current dating arc to a committed Partner.

    Refuses if not dating, chemistry too low, or already partnered.
    The Relationship flips ``kind`` Dating → Partner, the Agent flips
    ``role`` Dating → Partner, and ``state.dating`` clears.
    """
    if state.dating is None:
        return False, "You're not dating anyone to commit to."
    if _find_partner_relationship(state) is not None:
        return False, "You're already in a committed relationship."
    if state.dating["chemistry"] < COMMIT_CHEMISTRY_THRESHOLD:
        return False, (
            "You don't feel ready to commit yet. "
            "(You need at least "
            f"{COMMIT_CHEMISTRY_THRESHOLD} chemistry — go on more dates.)"
        )

    npc_id = state.dating["npc_id"]
    name = state.dating["name"]
    rel = _find_dating_relationship(state)
    if rel is not None:
        rel.kind = "Partner"
        rel.relationship = max(rel.relationship, 75)
    agent = _find_agent(state, npc_id)
    if agent is not None:
        agent.role = "Partner"
        agent.marital_status = "Partnered"
    state.dating = None
    return True, f"You and {name} are officially together."


def break_up(state: GameState) -> tuple[bool, str]:
    """End the current romance, dating or partner.

    Order of precedence: clears a dating prospect first (it's the more
    recent attachment) only if no Partner exists. With a Partner present,
    the Partner ends — that's the bigger commitment to dissolve.

    The ex-partner's Agent stays in state.agents (they're still a person
    in the world); only the Relationship link is removed so the player no
    longer counts them as romantic for predicates like consider_child.
    """
    if state.dating is None and _find_partner_relationship(state) is None:
        return False, "You're not in a relationship to end."

    # Partner end takes priority — committed first, dating prospects rarely
    # outlive a marriage in the same year.
    partner = _find_partner_relationship(state)
    if partner is not None:
        name = partner.name
        state.relationships = [r for r in state.relationships if r is not partner]
        # The ex stays as an Agent (people don't vanish from the world).
        agent = _find_agent(state, partner.npc_id)
        if agent is not None:
            agent.role = "Ex"
            agent.marital_status = "Single"
        return True, f"You and {name} broke up. The flat felt enormous for a while."

    # Otherwise, end the dating arc.
    arc = state.dating
    assert arc is not None  # narrowed by the no-romance guard at the top
    name = arc["name"]
    npc_id = arc["npc_id"]
    state.relationships = [r for r in state.relationships if r.npc_id != npc_id]
    agent = _find_agent(state, npc_id)
    if agent is not None:
        agent.role = "Ex"
    state.dating = None
    return True, f"You stopped seeing {name}. It wasn't right."
