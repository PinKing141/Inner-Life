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


# Gift catalogue — picker shown when the player taps Give Gift. Mix of
# tiered prices and rel boosts so the player makes a real choice, not
# just "always pick the biggest". Free option included so even a broke
# player can do something thoughtful.
GIFTS: tuple[dict, ...] = (
    {"id": "handmade_card",  "name": "Handmade card",  "price":     0, "rel_boost":  3,
     "blurb": "Free. The thought is real."},
    {"id": "flowers",        "name": "Flowers",        "price":    20, "rel_boost":  6,
     "blurb": "Reliable. Don't get the supermarket bunch."},
    {"id": "chocolates",     "name": "Box of chocolates", "price":  35, "rel_boost":  7,
     "blurb": "Always welcome. Pick something a tier above petrol-station."},
    {"id": "good_bottle",    "name": "Good bottle of wine", "price": 60, "rel_boost": 10,
     "blurb": "Costs more than they'd buy themselves."},
    {"id": "bracelet",       "name": "Bracelet",       "price":   180, "rel_boost": 15,
     "blurb": "Quietly considered. Keeps for years."},
    {"id": "watch",          "name": "Watch",          "price":   450, "rel_boost": 22,
     "blurb": "A real present. They'll wear it."},
    {"id": "designer_bag",   "name": "Designer bag",   "price":  1_800, "rel_boost": 32,
     "blurb": "Logos do the talking. Felt heavy in the box."},
    {"id": "luxury_jewellery","name": "Luxury jewellery","price": 6_000, "rel_boost": 45,
     "blurb": "A gift that becomes a story."},
)

# Money-gift tiers — discrete amounts so the picker is short and the
# player makes a values decision, not a slider one.
MONEY_GIFTS: tuple[dict, ...] = (
    {"id": "small",    "amount":     50, "rel_boost":  4, "blurb": "Token gesture."},
    {"id": "medium",   "amount":    500, "rel_boost": 10, "blurb": "Real help, no fuss."},
    {"id": "large",    "amount":  5_000, "rel_boost": 22, "blurb": "Life-easing money."},
    {"id": "huge",     "amount": 20_000, "rel_boost": 35, "blurb": "Changes their year."},
)

# Borrow gates: NPC needs to be close enough AND have money to lend.
BORROW_MIN_RELATIONSHIP = 50
BORROW_NPC_MIN_MONEY = 1_000
# Ask-for-advice gate: shallow ties don't share useful counsel.
ADVICE_MIN_RELATIONSHIP = 30

INTERACTIONS = (
    "talk", "compliment", "argue", "apologize",
    "conversation", "ask_advice", "hang_out",
    "give_gift", "give_money", "borrow_money",
    "insult",
)


def _find_agent(state: GameState, npc_id: int):
    for a in state.agents:
        if a.npc_id == npc_id:
            return a
    return None


def _find_gift(gift_id: str) -> dict | None:
    return next((g for g in GIFTS if g["id"] == gift_id), None)


def _find_money_gift(tier_id: str) -> dict | None:
    return next((m for m in MONEY_GIFTS if m["id"] == tier_id), None)


def interact(
    state: GameState,
    npc_id: int,
    action: str,
    *,
    rng=None,
    param: str | None = None,
) -> ActionResult:
    """Player-initiated interaction with a known NPC. Returns (ok, message).

    ``param`` is used by the picker verbs:
      * ``give_gift`` — ``param`` is a gift id from ``GIFTS``.
      * ``give_money`` — ``param`` is a tier id from ``MONEY_GIFTS``.

    Some verbs (``conversation``, ``ask_advice``, ``borrow_money``) use
    the passed-in ``rng`` for rng-driven outcomes; deterministic verbs
    ignore it. The controller forks an rng off the current tick + feed
    length so repeated interactions in one year still diverge.
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

    if action == "conversation":
        # The longer version of "talk" — a real conversation. ~70% of
        # the time it lands; the rest it surfaces something harder and
        # costs a little emotional reserve.
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
        agent = _find_agent(state, npc_id)
        npc_smarts = agent.smarts if agent is not None else 50
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

    if action == "hang_out":
        # Free verb with a generous lift — the everyday default the
        # player can lean on. Cheaper than dinner, less effort than
        # conversation, no rng surprise.
        rel.relationship = min(100, rel.relationship + 5)
        state.stats.happiness = min(100, state.stats.happiness + 3)
        return ActionResult(True, f"You hung out with {name}. Easy, nice.")

    if action == "give_gift":
        gift = _find_gift(param) if param else None
        if gift is None:
            return ActionResult(False, "Pick a gift first.")
        if state.money < gift["price"]:
            return ActionResult(False,
                f"You can't afford a {gift['name'].lower()} (£{gift['price']:,}).")
        state.money -= gift["price"]
        rel.relationship = min(100, rel.relationship + gift["rel_boost"])
        # Free gifts still cost happiness gain less; expensive ones lift
        # the player's mood too.
        if gift["price"] >= 1_000:
            state.stats.happiness = min(100, state.stats.happiness + 3)
        if gift["price"] > 0:
            return ActionResult(True,
                f"You gave {name} a {gift['name'].lower()}. £{gift['price']:,}.")
        return ActionResult(True,
            f"You gave {name} a {gift['name'].lower()}. The thought was the point.")

    if action == "give_money":
        tier = _find_money_gift(param) if param else None
        if tier is None:
            return ActionResult(False, "Pick how much to give.")
        amount = tier["amount"]
        if state.money < amount:
            return ActionResult(False,
                f"You can't afford to give £{amount:,} right now.")
        state.money -= amount
        agent = _find_agent(state, npc_id)
        if agent is not None:
            agent.money += amount  # conservation: money moves to the NPC
        rel.relationship = min(100, rel.relationship + tier["rel_boost"])
        state.stats.happiness = min(100, state.stats.happiness + 2)
        return ActionResult(True,
            f"You gave {name} £{amount:,}. They were grateful.")

    if action == "borrow_money":
        if rel.relationship < BORROW_MIN_RELATIONSHIP:
            return ActionResult(False,
                f"Your relationship with {name} isn't close enough to ask for money.")
        agent = _find_agent(state, npc_id)
        npc_money = agent.money if agent is not None else 0
        if npc_money < BORROW_NPC_MIN_MONEY:
            return ActionResult(False, f"{name} doesn't have it to lend right now.")
        lend_chance = 0.30 + (rel.relationship / 100.0) * 0.55
        will_lend = rng.fork(0xB07).chance(lend_chance) if rng is not None else True
        if will_lend:
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

    return ActionResult(False, "You can't do that.")
    return ActionResult(False, "You can't do that.")
