"""Phase 5 — genealogy: children, inheritance, continuing as your heir.

The simulation already carried the *data shape* for dynasties (Character has
``parents``, ``children``, ``lineage_id``). What was missing was the actual
mechanic of having a child, dying, and continuing as one — turning a
single life into a family line.

Three responsibilities:

1. **Birth** (``have_child``) — when the player accepts the consider_child
   event, mint a child Agent (age 0), append their npc_id to the player's
   Character.children, and write a feed entry.

2. **Eligible heirs** (``eligible_heirs``) — which children are still alive
   at the moment of the player's death.

3. **Continue as heir** (``continue_as_heir``) — archive the outgoing life
   into ``state.ancestors``, swap the player Character for the heir, carry
   inherited money minus an estate tax, preserve the lineage_id, reset
   per-life systems (career, education, feed, exam, pending popups), and
   flip ``mode`` back to PLAYING.

Estate model is deliberately minimal — see ``ESTATE_TAX_PCT`` /
``estate_share_for``. Property doesn't transfer in this slice; only liquid
money. Rumour-style "your father was famous" social hooks are queued.

Design rules:

- Determinism preserved: the only randomness here is at child-birth time,
  forked off the engine's tick rng (callers pass an rng in).
- This module is the only place that mutates GameState across a generational
  boundary. Everything else continues to think one-life-at-a-time.
"""
from __future__ import annotations

from typing import Optional

from core.content import names as names_mod
from core.rng import Rng
from core.state import (
    Character,
    Education,
    FeedEntry,
    GameState,
    Job,
    Relationship,
    Stats,
)


# Inherited liquid wealth is split among living children, minus a fixed
# estate tax. Numbers are intentionally simple; the design exists.
ESTATE_TAX_PCT = 0.40

# When a fresh life starts from an heir, these subsystems reset entirely.
# Anything that's *life-scoped* (career, school, feed) gets a clean slate;
# anything *world-scoped* (era, inflation, lineage) survives the transition.


# --- Helpers ---------------------------------------------------------------


def _next_npc_id(state: GameState) -> int:
    """Hand out the next free npc_id, stepping past every record currently
    in the world (agents + the player-side relationships)."""
    max_agent = max((a.npc_id for a in state.agents), default=0)
    max_rel = max((r.npc_id for r in state.relationships), default=0)
    return max(max_agent, max_rel) + 1


def _find_agent(state: GameState, npc_id: int):
    for a in state.agents:
        if a.npc_id == npc_id:
            return a
    return None


# --- Birth -----------------------------------------------------------------


def have_child(state: GameState, rng: Rng) -> Optional[str]:
    """Mint a child Agent for the player, age 0. Returns a feed-worthy
    sentence ("You and your partner welcomed a baby girl, Helena.") or
    None if conditions can't be satisfied (no character, no partner).

    Side effects:
      - new Agent appended to state.agents with role="Child"
      - new Relationship appended (kind="Child") so the UI can surface
        the child on the Relations screen immediately
      - player's Character.children list gains the new npc_id
      - a small happiness bump (the verb is happy news)
    """
    from core.agents import Agent  # local to dodge cycle

    if state.character is None:
        return None
    partner = next(
        (r for r in state.relationships if r.kind == "Partner" and r.alive),
        None,
    )
    if partner is None:
        return None

    surname = state.character.last_name
    country = state.character.country
    city = state.character.city

    gender = rng.fork(1).choice(["Male", "Female", "NonBinary"])
    first_name = names_mod.random_forename(country, gender, rng.fork(2))
    npc_id = _next_npc_id(state)

    # Light Mendelian-flavoured rolls — bias toward the average of the
    # two parents on visible stats, then jitter. Smarts/looks are the
    # heritable ones; health is rolled fresh. Player's stats stand in
    # for one parent; the partner's are unknown to us at this level so
    # we approximate with 60 (a typical adult midpoint).
    p_smarts = state.stats.smarts
    p_looks = state.stats.looks
    smarts = max(0, min(100, (p_smarts + 60) // 2 + rng.fork(3).randint(-10, 10)))
    looks = max(0, min(100, (p_looks + 60) // 2 + rng.fork(4).randint(-10, 10)))
    health = 80 + rng.fork(5).randint(0, 20)

    child = Agent(
        npc_id=npc_id,
        first_name=first_name,
        last_name=surname,
        gender=gender,
        role="Child",
        age=0,
        country=country,
        city=city,
        health=health,
        happiness=80,
        smarts=smarts,
        looks=looks,
        generosity=rng.fork(6).randint(20, 80),
        money=0,
        job_title=None,
        marital_status="Single",
        education="None",
        alive=True,
    )
    state.agents.append(child)
    state.relationships.append(Relationship(
        npc_id=npc_id, name=child.name, kind="Child", relationship=85, alive=True,
    ))
    state.character.children.append(npc_id)

    state.stats.happiness = min(100, state.stats.happiness + 6)
    descriptor = {"Male": "baby boy", "Female": "baby girl"}.get(gender, "baby")
    return f"You and {partner.name} welcomed a {descriptor}, {first_name}."


# --- Eligibility & estate --------------------------------------------------


def eligible_heirs(state: GameState) -> list[dict]:
    """Living children of the current player, in npc_id order.

    Stable, JSON-friendly: each entry is a dict the controller can drop
    into the snapshot for the UI to render heir buttons. Returns [] if
    no living children — the death modal then degrades to plain
    'End of Life' as before."""
    if state.character is None:
        return []
    out: list[dict] = []
    for child_id in sorted(state.character.children):
        agent = _find_agent(state, child_id)
        if agent is None or not agent.alive:
            continue
        out.append({
            "npc_id": agent.npc_id,
            "name": agent.name,
            "age": agent.age,
            "gender": agent.gender,
        })
    return out


def estate_share_for(state: GameState, heir_npc_id: int) -> int:
    """How much liquid money the chosen heir inherits.

    Net estate = max(0, money) * (1 - tax), split evenly across LIVING
    heirs at the moment of death. Negative balances don't carry — debt
    dies with the player (simple, forgiving; we can revisit later).
    The chosen heir collects their share."""
    living = eligible_heirs(state)
    if not living:
        return 0
    if not any(h["npc_id"] == heir_npc_id for h in living):
        return 0
    net = max(0, state.money)
    after_tax = int(net * (1 - ESTATE_TAX_PCT))
    return after_tax // len(living)


# --- Generational transition ----------------------------------------------


def snapshot_for_archive(state: GameState) -> dict:
    """Compress the outgoing life into a dict for state.ancestors.

    Captures just enough for legend / family-history reads: who they
    were, what they did, what they had. Deliberately not the full
    GameState — that'd bloat saves indefinitely as generations stack.
    """
    char = state.character
    if char is None:
        return {}
    return {
        "first_name": char.first_name,
        "last_name": char.last_name,
        "gender": char.gender,
        "country": char.country,
        "city": char.city,
        "talent": char.talent,
        "lineage_id": char.lineage_id,
        "age_at_death": char.age,
        "final_stats": state.stats.to_dict(),
        "final_money": state.money,
        "final_career_title": state.career.title if state.career else None,
        "education_level": state.education.level,
        "children": list(char.children),
    }


def continue_as_heir(state: GameState, heir_npc_id: int) -> bool:
    """Pivot the GameState onto a chosen heir as the new playable character.

    Returns True if the transition happened. Refuses (False) when:
      - the game isn't in DEATH mode (continuing only after death),
      - the heir doesn't exist among the player's children, or
      - the heir is no longer alive.

    On success:
      - Outgoing Character is archived into ``state.ancestors``.
      - Heir's Agent is removed from state.agents (they're now the
        player, not an NPC).
      - A fresh Character is built from the heir's Agent record;
        lineage_id is preserved. The player Character.parents list
        points at the previous-generation Character.
      - Liquid money is replaced by the heir's estate share.
      - Per-life subsystems (career, education, feed, exam, pending
        popups, fired_events, causal_chain) reset. World state survives.
      - ``state.mode`` flips back to PLAYING; a generational feed entry
        marks the transition.
    """
    if state.mode != "DEATH" or state.character is None:
        return False
    heir_agent = _find_agent(state, heir_npc_id)
    if heir_agent is None or not heir_agent.alive:
        return False
    if heir_npc_id not in state.character.children:
        return False

    # 1. Archive the outgoing life.
    archive = snapshot_for_archive(state)
    state.ancestors.append(archive)

    # 2. Inheritance figure (must be computed BEFORE we mutate state.money).
    share = estate_share_for(state, heir_npc_id)
    parent_first = state.character.first_name
    parent_last = state.character.last_name

    # 3. Build the new Character from the heir's Agent.
    new_character = Character(
        first_name=heir_agent.first_name,
        last_name=heir_agent.last_name,
        gender=heir_agent.gender,
        country=heir_agent.country,
        city=heir_agent.city,
        talent="",  # heirs don't pre-pick a talent; the system can prompt later
        age=heir_agent.age,
        alive=True,
        parents=[],   # populated below in parent_details for narrative
        children=[],  # fresh line
        lineage_id=state.character.lineage_id,  # PRESERVED across generations
        birth_story=f"born to {parent_first} {parent_last}, your forebear",
        parent_details=[{
            "name": f"{parent_first} {parent_last}".strip(),
            "role": "Parent",
            "age_at_birth": archive.get("age_at_death", 0) - heir_agent.age,
            "job": archive.get("final_career_title"),
        }],
    )

    # 4. Heir Agent leaves the NPC list — they ARE the player now.
    state.agents = [a for a in state.agents if a.npc_id != heir_npc_id]

    # 4b. Rebuild the heir's player-facing relationships from the heir's
    # perspective. The previous player's social graph belonged to them,
    # not to the heir: their Partner is the heir's *other parent*, not
    # the heir's spouse; their Friends/Coworkers are strangers to the
    # heir; their Mother/Father are the heir's grandparents (usually
    # long dead). Carrying any of that across would let the sim treat
    # the heir as romantically partnered to a step-parent the first
    # time consider_child or tick_partner runs. Rebuild instead of
    # filter — narrow, explicit, defensible.
    prev_partner_id = next(
        (r.npc_id for r in state.relationships
         if r.kind == "Partner" and r.alive and r.npc_id != heir_npc_id),
        None,
    )
    other_child_ids = [c for c in state.character.children if c != heir_npc_id]
    new_relationships: list[Relationship] = []

    # Surviving partner of the deceased -> heir's other biological parent.
    # Mother / Father is read from the partner Agent's gender.
    if prev_partner_id is not None:
        partner_agent = next(
            (a for a in state.agents if a.npc_id == prev_partner_id), None,
        )
        if partner_agent is not None and partner_agent.alive:
            parent_kind = (
                "Mother" if partner_agent.gender == "Female"
                else "Father" if partner_agent.gender == "Male"
                else "Parent"
            )
            partner_agent.role = parent_kind  # keep Agent.role consistent
            new_relationships.append(Relationship(
                npc_id=prev_partner_id, name=partner_agent.name,
                kind=parent_kind, relationship=85, alive=True,
            ))

    # Other living children of the deceased -> heir's siblings.
    for sib_id in other_child_ids:
        sib_agent = next((a for a in state.agents if a.npc_id == sib_id), None)
        if sib_agent is None or not sib_agent.alive:
            continue
        sib_agent.role = "Sibling"
        new_relationships.append(Relationship(
            npc_id=sib_id, name=sib_agent.name,
            kind="Sibling", relationship=70, alive=True,
        ))

    state.relationships = new_relationships

    # 5. Stats — re-roll lightly from the heir's Agent stats (those were
    # already shaped at birth by parental inheritance).
    state.stats = Stats(
        happiness=80,
        health=max(50, heir_agent.health),
        smarts=heir_agent.smarts,
        looks=heir_agent.looks,
    ).clamped()

    # 6. Per-life resets. World state survives the transition.
    state.character = new_character
    state.mode = "PLAYING"
    state.money = share
    state.career = None
    state.education = Education()
    state.exam = None
    state.pending_event_id = None
    state.pending_job_offer = None
    state.pending_promotion = None
    state.pending_job_loss = None
    state.pending_career_setback = None
    state.job_application_error = None
    state.fired_events = []
    state.causal_chain = []
    state.feed = []
    # Note: properties don't carry over in MVP — sold at probate, value
    # already counted in `money` would be too much complexity here. Future
    # work can route real estate through estate distribution.
    state.properties = []
    state.rental = None
    state.last_help_tick = -100
    # tick keeps going; we're in the same world, just at a new life.

    state.feed.append(FeedEntry(
        age=new_character.age,
        text=(
            f"Your forebear {parent_first} {parent_last} passed on. "
            f"You inherited £{share:,} and the {new_character.last_name} name."
        ),
        kind="special",
        entry_id=f"feed:lineage:{state.tick}:{heir_npc_id}",
    ))
    return True
