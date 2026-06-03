"""Social graph (player-facing slice).

`Relationship` is a thin player-side view of an `Agent` (see core.agents).
This module owns the player's initial family, the bump/drift loop, and any
direct player↔NPC mutation. Anything that ticks an NPC itself lives in
`core.agents`.
"""
from __future__ import annotations

from core.content import names as names_mod
from core.results import ActionResult
from core.rng import Rng
from core.state import GameState, Relationship


def seed_family(
    state: GameState,
    rng: Rng | None = None,
    *,
    mother_name: str | None = None,
    father_name: str | None = None,
) -> None:
    """Spawn the player's parents at birth with culture-appropriate names."""
    rng = rng or Rng(state.seed ^ 0xA1B2C3)
    country = state.character.country if state.character else ""
    surname = state.character.last_name if state.character else ""

    mum_first = names_mod.random_forename(country, "Female", rng.fork(1))
    dad_first = names_mod.random_forename(country, "Male", rng.fork(2))
    # Keep parents on the player's surname for clarity in the early UI.
    mum_name = mother_name or f"{mum_first} {surname}".strip()
    dad_name = father_name or f"{dad_first} {surname}".strip()

    state.relationships.append(Relationship(npc_id=1, name=mum_name, kind="Mother", relationship=90))
    state.relationships.append(Relationship(npc_id=2, name=dad_name, kind="Father", relationship=90))


def spend_time_with_family(state: GameState) -> None:
    for r in state.relationships:
        if r.kind in ("Mother", "Father", "Sibling") and r.alive:
            r.relationship = min(100, r.relationship + 5)


WEAK_TIE_KINDS = ("Friend", "Coworker")


def annual_drift(state: GameState) -> None:
    """Relationships decay slightly if not maintained.

    Weak ties (friends, coworkers) that decay all the way to zero drift out of
    the player's life entirely — pruned from the list — so the graph has a way
    to lose members short of death, which the renewal mechanic then refills.
    Family and partners never drift out this way (only death removes them).
    """
    survivors = []
    for r in state.relationships:
        if r.alive:
            if r.kind != "Partner":  # partnerships persist; they don't passively erode
                r.relationship = max(0, r.relationship - 1)
            if r.relationship <= 0 and r.kind in WEAK_TIE_KINDS:
                continue  # drifted apart
        survivors.append(r)
    state.relationships = survivors


# --- Isolation consequence (decay vertical slice) ---
# Decay already nibbles relationships every year; this gives that decay teeth.
# When the player has no remaining strong tie, isolation costs happiness — so
# letting the social graph rot is now a real pressure, not just a number going
# down. The narrative line is rate-limited (via tick) so it doesn't spam.
LONELY_KINDS = ("Mother", "Father", "Sibling", "Partner", "Friend")
LONELY_THRESHOLD = 25
LONELY_PENALTY = 2


def loneliness_tick(state: GameState) -> str | None:
    """Apply a happiness penalty when the player is socially isolated.

    Returns a feed-worthy note on the years it surfaces, else None. The
    penalty itself applies every isolated year regardless of the note.
    """
    if state.character is None:
        return None
    close = [r for r in state.relationships if r.alive and r.kind in LONELY_KINDS]
    support = max((r.relationship for r in close), default=0)
    if support >= LONELY_THRESHOLD:
        return None
    state.stats.happiness = max(0, state.stats.happiness - LONELY_PENALTY)
    if state.tick % 5 == 0:
        return "You feel increasingly lonely and disconnected from those around you."
    return None


GIFT_COST = 50
LAVISH_GIFT_COST = 500
DINNER_COST = 80
# Borrow gates: NPC needs to be close enough AND have money to lend.
BORROW_MIN_RELATIONSHIP = 50
BORROW_NPC_MIN_MONEY = 1_000
# Ask-for-advice gate: shallow ties don't share useful counsel.
ADVICE_MIN_RELATIONSHIP = 30

INTERACTIONS = (
    "talk", "compliment", "argue", "gift",
    "apologize", "deep_talk", "ask_advice", "borrow_money",
    "insult", "lavish_gift", "take_to_dinner",
)


def _find_agent(state: GameState, npc_id: int):
    for a in state.agents:
        if a.npc_id == npc_id:
            return a
    return None


def interact(state: GameState, npc_id: int, action: str, rng=None) -> ActionResult:
    """Player-initiated interaction with a known NPC. Returns (ok, message).

    State is only mutated on success. Some verbs (``deep_talk``,
    ``ask_advice``, ``borrow_money``) use the passed-in ``rng`` for
    rng-driven outcomes; deterministic verbs ignore it. The controller
    forks an rng off the current tick + feed length per call so repeated
    interactions in one year still diverge.
    """
    rel = next((r for r in state.relationships if r.npc_id == npc_id), None)
    if rel is None:
        return ActionResult(False, "You don't know that person.")
    name = rel.name
    if not rel.alive:
        return ActionResult(False, f"{name} has passed away.")

    if action == "talk":
        rel.relationship = min(100, rel.relationship + 3)
        state.stats.happiness = min(100, state.stats.happiness + 1)
        return ActionResult(True, f"You had a nice chat with {name}.")
    if action == "compliment":
        rel.relationship = min(100, rel.relationship + 5)
        return ActionResult(True, f"You complimented {name}. They appreciated it.")
    if action == "argue":
        rel.relationship = max(0, rel.relationship - 8)
        state.stats.happiness = max(0, state.stats.happiness - 3)
        return ActionResult(True, f"You got into an argument with {name}.")
    if action == "gift":
        if state.money < GIFT_COST:
            return ActionResult(False, f"You can't afford a gift for {name}.")
        state.money -= GIFT_COST
        rel.relationship = min(100, rel.relationship + 10)
        return ActionResult(True, f"You gave {name} a gift. It cost £{GIFT_COST}.")

    # --- New verbs (Phase 6 — NPC verbs v1) -----------------------------

    if action == "apologize":
        # Big lift when the relationship is hurt (rel < 50), small
        # acknowledgement otherwise. Models real apologies: meaningful
        # when there's something to fix, performative when there isn't.
        if rel.relationship < 50:
            rel.relationship = min(100, rel.relationship + 12)
            state.stats.happiness = min(100, state.stats.happiness + 2)
            return ActionResult(True, f"You apologised to {name}. They softened.")
        rel.relationship = min(100, rel.relationship + 2)
        return ActionResult(True, f"You said sorry. {name} wasn't sure what for.")

    if action == "deep_talk":
        # Heart-to-heart. ~70% of the time it lands; the rest it surfaces
        # something harder and costs a little emotional reserve.
        good_roll = rng.fork(0xD1A).chance(0.70) if rng is not None else True
        if good_roll:
            rel.relationship = min(100, rel.relationship + 6)
            state.stats.happiness = min(100, state.stats.happiness + 4)
            state.stats.health = max(0, state.stats.health - 1)
            return ActionResult(True, f"A real conversation with {name}. You both meant it.")
        rel.relationship = min(100, rel.relationship + 2)
        state.stats.happiness = max(0, state.stats.happiness - 2)
        return ActionResult(True, f"You opened up to {name}. It got heavy, briefly.")

    if action == "ask_advice":
        if rel.relationship < ADVICE_MIN_RELATIONSHIP:
            return ActionResult(False,
                f"You don't know {name} well enough to ask for real advice.")
        # Advice quality scales with the NPC's own smarts (read from
        # the Agent record). Better counsel from sharper people. A
        # bad roll surfaces unhelpful guidance.
        agent = _find_agent(state, npc_id)
        npc_smarts = agent.smarts if agent is not None else 50
        # Chance scales with NPC smarts: 50 smarts = 60% useful, 100 = 95%.
        useful_chance = 0.40 + (npc_smarts / 100.0) * 0.55
        useful = rng.fork(0xADC).chance(useful_chance) if rng is not None else True
        if useful:
            state.stats.smarts = min(100, state.stats.smarts + 3)
            rel.relationship = min(100, rel.relationship + 4)
            return ActionResult(True,
                f"You asked {name} for advice. Their take stuck with you.")
        rel.relationship = min(100, rel.relationship + 1)
        return ActionResult(True,
            f"You asked {name} for advice. It wasn't what you needed.")

    if action == "borrow_money":
        if rel.relationship < BORROW_MIN_RELATIONSHIP:
            return ActionResult(False,
                f"Your relationship with {name} isn't close enough to ask for money.")
        agent = _find_agent(state, npc_id)
        npc_money = agent.money if agent is not None else 0
        if npc_money < BORROW_NPC_MIN_MONEY:
            return ActionResult(False, f"{name} doesn't have it to lend right now.")
        # Lend chance scales with relationship strength. Even close ties
        # sometimes say no — there's real social cost in the ask.
        lend_chance = 0.30 + (rel.relationship / 100.0) * 0.55
        will_lend = rng.fork(0xB07).chance(lend_chance) if rng is not None else True
        if will_lend:
            # Amount scales with both: closer ties + richer lenders give more.
            base = min(npc_money, 2_000)
            amount = int(base * (0.5 + rel.relationship / 200.0))
            amount = max(100, min(amount, npc_money))
            state.money += amount
            if agent is not None:
                agent.money = max(0, agent.money - amount)
            rel.relationship = max(0, rel.relationship - 5)
            return ActionResult(True,
                f"{name} lent you £{amount:,}. They didn't make it a thing.")
        rel.relationship = max(0, rel.relationship - 8)
        state.stats.happiness = max(0, state.stats.happiness - 3)
        return ActionResult(True,
            f"{name} said no. It was awkward for weeks.")

    if action == "insult":
        rel.relationship = max(0, rel.relationship - 15)
        state.stats.happiness = max(0, state.stats.happiness - 4)
        state.stats.looks = max(0, state.stats.looks - 1)
        return ActionResult(True, f"You said something cruel to {name}. It stuck.")

    if action == "lavish_gift":
        if state.money < LAVISH_GIFT_COST:
            return ActionResult(False,
                f"You can't afford a serious gift for {name} (£{LAVISH_GIFT_COST}).")
        state.money -= LAVISH_GIFT_COST
        rel.relationship = min(100, rel.relationship + 20)
        state.stats.happiness = min(100, state.stats.happiness + 3)
        return ActionResult(True,
            f"You gave {name} something genuinely thoughtful. £{LAVISH_GIFT_COST}.")

    if action == "take_to_dinner":
        if state.money < DINNER_COST:
            return ActionResult(False,
                f"You can't afford to take {name} out (£{DINNER_COST}).")
        state.money -= DINNER_COST
        rel.relationship = min(100, rel.relationship + 8)
        state.stats.happiness = min(100, state.stats.happiness + 3)
        return ActionResult(True,
            f"You took {name} for a long dinner. Worth £{DINNER_COST}.")

    return ActionResult(False, "You can't do that.")
