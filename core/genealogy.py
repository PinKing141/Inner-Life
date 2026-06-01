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

from typing import TYPE_CHECKING, Optional

from core.content import names as names_mod

if TYPE_CHECKING:
    from core.agents import Agent
from core.rng import Rng
from core.state import (
    Character,
    Education,
    FeedEntry,
    GameState,
    Job,
    PregnancyState,
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


def _mint_child(
    state: GameState,
    rng: Rng,
    *,
    partner_npc_id: int | None,
    partner_name: str,
    partner_looks: int,
    partner_smarts: int,
) -> tuple[Optional["Agent"], Optional[str]]:
    """Shared internal: spawn a baby Agent + Relationship + Character.children
    record, with genetic stats blended from BOTH parents.

    Genetic model
    -------------
    Smarts and looks are heritable: child's stat = average(player, partner)
    ± 10 jitter. Health is rolled fresh (modelling environment + lottery,
    not lineage). The partner's stats are read at call time — callers that
    care about determinism (pregnancy resolution) snapshot them at
    conception and pass them in here.

    Returns the new Agent (or None if no character) and a feed sentence.
    Callers decide whether to suppress the sentence (e.g. when the naming
    modal is going to print its own).
    """
    from core.agents import Agent  # local to dodge cycle

    if state.character is None:
        return None, None

    surname = state.character.last_name
    country = state.character.country
    city = state.character.city

    gender = rng.fork(1).choice(["Male", "Female", "NonBinary"])
    first_name = names_mod.random_forename(country, gender, rng.fork(2))
    npc_id = _next_npc_id(state)

    p_smarts = state.stats.smarts
    p_looks = state.stats.looks
    smarts = max(0, min(100, (p_smarts + partner_smarts) // 2 + rng.fork(3).randint(-10, 10)))
    looks = max(0, min(100, (p_looks + partner_looks) // 2 + rng.fork(4).randint(-10, 10)))
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
    parent_phrase = partner_name or "your partner"
    return child, f"You and {parent_phrase} welcomed a {descriptor}, {first_name}."


def have_child(state: GameState, rng: Rng) -> Optional[str]:
    """Instant-birth path (used by the `have_child` event side_effect in
    legacy / tests). Reads the player's living Partner's Agent stats so
    genetics are two-parent. Returns the feed sentence or None.

    Most births should go through ``begin_pregnancy`` /
    ``resolve_pregnancy`` instead — this helper exists for backwards
    compatibility and as the fallback when callers don't need a one-year
    gestation cycle.
    """
    if state.character is None:
        return None
    partner = next(
        (r for r in state.relationships if r.kind == "Partner" and r.alive),
        None,
    )
    if partner is None:
        return None
    partner_agent = _find_agent(state, partner.npc_id)
    _, msg = _mint_child(
        state, rng,
        partner_npc_id=partner.npc_id,
        partner_name=partner.name,
        partner_looks=partner_agent.looks if partner_agent else 60,
        partner_smarts=partner_agent.smarts if partner_agent else 60,
    )
    return msg


# --- Pregnancy v1 ----------------------------------------------------------


# Age fertility band for the carrier. Conception probability falls off
# sharply past 35 (modelling real-life fertility curves at a coarse level).
CARRIER_MIN_AGE = 16
CARRIER_MAX_AGE = 50
# Per-call probability when attempt_conception goes through the random
# pathway (e.g. broken_condom event). Modulated by health.
BASE_CONCEPTION_PROB_YOUNG = 0.80   # under 30
BASE_CONCEPTION_PROB_MID = 0.40     # 30–34
BASE_CONCEPTION_PROB_OLDER = 0.15   # 35–50
# Complication rate at birth. Stays explicitly low to keep v1 forgiving.
MISCARRIAGE_PROB = 0.05


def _snapshot_partner(state: GameState) -> tuple[int | None, str, int, int]:
    """Return (npc_id, name, looks, smarts) for the player's living Partner,
    falling back to midpoint stats if there's no Agent record. Used to
    freeze the partner's genetic contribution at conception time."""
    partner = next(
        (r for r in state.relationships if r.kind == "Partner" and r.alive),
        None,
    )
    if partner is None:
        return None, "", 60, 60
    agent = _find_agent(state, partner.npc_id)
    looks = agent.looks if agent else 60
    smarts = agent.smarts if agent else 60
    return partner.npc_id, partner.name, looks, smarts


def begin_pregnancy(state: GameState, *, player_is_carrier: bool = True) -> bool:
    """Unconditional pregnancy registration. Returns False only when the
    state is incoherent (no character, already pregnant, no living
    partner). The deliberate-choice path (consider_child "yes") goes
    through here so the player isn't denied by a probability roll after
    explicitly opting in.
    """
    if state.character is None or state.pregnancy.is_active:
        return False
    npc_id, name, looks, smarts = _snapshot_partner(state)
    if npc_id is None:
        return False
    state.pregnancy = PregnancyState(
        is_active=True,
        carrier_is_player=player_is_carrier,
        partner_npc_id=npc_id,
        conception_age=state.character.age,
        conception_tick=state.tick,
        partner_looks=looks,
        partner_smarts=smarts,
        partner_name=name,
    )
    return True


def attempt_conception(state: GameState, rng: Rng, *, player_is_carrier: bool = True) -> bool:
    """Probabilistic pregnancy roll. Returns True if conception happened.

    Refuses (returns False without rolling) when the carrier is outside
    the fertility band, the player already has an active pregnancy, or
    there's no living partner to attribute parentage to.

    The probability curve is age-banded and health-modulated. Health < 50
    drags the chance down linearly.
    """
    if state.character is None or state.pregnancy.is_active:
        return False
    carrier_age = state.character.age  # v1: player carries OR carrier age == player age (modelled simply)
    if carrier_age < CARRIER_MIN_AGE or carrier_age > CARRIER_MAX_AGE:
        return False
    npc_id, name, looks, smarts = _snapshot_partner(state)
    if npc_id is None:
        return False

    if carrier_age < 30:
        base = BASE_CONCEPTION_PROB_YOUNG
    elif carrier_age < 35:
        base = BASE_CONCEPTION_PROB_MID
    else:
        base = BASE_CONCEPTION_PROB_OLDER
    health_factor = max(0.3, state.stats.health / 100.0)
    final = base * health_factor

    if not rng.chance(final):
        return False

    state.pregnancy = PregnancyState(
        is_active=True,
        carrier_is_player=player_is_carrier,
        partner_npc_id=npc_id,
        conception_age=state.character.age,
        conception_tick=state.tick,
        partner_looks=looks,
        partner_smarts=smarts,
        partner_name=name,
    )
    return True


def resolve_pregnancy(state: GameState, rng: Rng) -> Optional[dict]:
    """Called from sim.age_up the year AFTER conception. Either:
      - rolls a miscarriage (small chance) and writes a feed entry, or
      - mints the child via ``_mint_child`` and sets ``state.pending_birth``
        for the UI naming modal.

    Returns the pending_birth payload on a successful birth, None on
    miscarriage or no-op. Always clears ``state.pregnancy.is_active``.
    """
    if not state.pregnancy.is_active or state.character is None:
        return None
    # Only resolve when at least one tick has passed since conception —
    # callers (sim.age_up) increment tick before calling, so the very
    # tick of conception doesn't immediately resolve.
    if state.tick <= state.pregnancy.conception_tick:
        return None

    preg = state.pregnancy
    state.pregnancy = PregnancyState()  # reset before any return

    if rng.fork(1).chance(MISCARRIAGE_PROB):
        # Miscarriage path. The feed line is intentionally restrained —
        # the player can read more into it than the engine spells out.
        state.stats.happiness = max(0, state.stats.happiness - 25)
        state.stats.health = max(0, state.stats.health - 5)
        state.feed.append(FeedEntry(
            age=state.character.age,
            text="You lost the pregnancy. It took a long time to find words for it.",
            kind="bad",
            entry_id=f"feed:miscarriage:{state.tick}",
        ))
        return None

    child, msg = _mint_child(
        state, rng.fork(2),
        partner_npc_id=preg.partner_npc_id,
        partner_name=preg.partner_name or "your partner",
        partner_looks=preg.partner_looks,
        partner_smarts=preg.partner_smarts,
    )
    if child is None:
        return None

    state.pending_birth = {
        "npc_id": child.npc_id,
        "gender": child.gender,
        "suggested_name": child.first_name,
        "last_name": child.last_name,
        "partner_name": preg.partner_name,
    }
    # Feed line gets a placeholder using the suggested name; if the player
    # picks a different name via the modal, name_child() patches the feed
    # entry in place.
    state.feed.append(FeedEntry(
        age=state.character.age,
        text=msg or "Your baby was born.",
        kind="special",
        entry_id=f"feed:birth:{state.tick}:{child.npc_id}",
    ))
    return state.pending_birth


def name_child(state: GameState, npc_id: int, chosen_name: str) -> bool:
    """Apply the player-picked name to a newly-born child. Returns False
    if the npc_id doesn't match the pending birth or the name is blank.

    Updates the Agent.first_name, the Relationship.name, and the
    most-recent feed entry (the auto-generated "you welcomed a baby"
    line) so the narrative reads consistently. Clears state.pending_birth.
    """
    if state.pending_birth is None or state.pending_birth.get("npc_id") != npc_id:
        return False
    clean = chosen_name.strip()
    if not clean:
        return False
    agent = _find_agent(state, npc_id)
    if agent is None:
        return False
    old_first = agent.first_name
    agent.first_name = clean
    # Refresh the matching Relationship's display name (Child.name mirrors
    # the agent — the player-facing list should not lag).
    for r in state.relationships:
        if r.npc_id == npc_id:
            r.name = agent.name
            break
    # Patch the feed entry that announced the birth so the chosen name
    # appears in the player's life log. Search from the tail because
    # birth lines land at the end of the year.
    for entry in reversed(state.feed):
        if entry.entry_id.startswith(f"feed:birth:") and old_first in entry.text:
            entry.text = entry.text.replace(old_first, clean)
            break
    state.pending_birth = None
    return True


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
    # Pregnancy v1: a new generation never inherits the deceased's
    # gestation state — that'd cause a phantom resolve on the heir's
    # first tick.
    state.pregnancy = PregnancyState()
    state.pending_birth = None
    state.pending_milestone = None
    state.milestones_seen = []
    # Crime v1: heirs start with a clean record — the dead never carry
    # their convictions into the next life.
    from core.state import CriminalRecord
    state.crime = CriminalRecord()
    state.pending_crime_outcome = None
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
