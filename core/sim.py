"""Core simulation tick.

This is the only place that 'a year passes' for the player. Anything that
should happen yearly — economy, education, NPC drift, random events, death
checks — runs from here, in a fixed order.

Determinism rule: given the same GameState and same Rng, calling `age_up`
must produce identical results every time.
"""
from __future__ import annotations

import uuid

from core import economy, education, events, relationships
from core.rng import Rng
from core.state import Character, FeedEntry, GameState, Stats


def new_game(seed: int, name: str, gender: str, country: str, talent: str) -> GameState:
    """Initialise a fresh life. Stats are biased by talent."""
    rng = Rng(seed)
    base_smarts = 50 + rng.randint(0, 20)
    base_looks = 50 + rng.randint(0, 20)
    base_health = 80 + rng.randint(0, 20)
    if talent == "Academics":
        base_smarts += 20
    elif talent == "Acting":
        base_looks += 20
    elif talent == "Sports":
        base_health += 20

    wealth_tiers = [0, 500, 2_000, 10_000]
    starting_wealth = rng.choice(wealth_tiers)

    state = GameState(
        seed=seed,
        mode="PLAYING",
        character=Character(name=name, gender=gender, country=country, talent=talent, age=0),
        stats=Stats(
            happiness=100,
            health=min(100, base_health),
            smarts=min(100, base_smarts),
            looks=min(100, base_looks),
        ),
        money=starting_wealth,
    )
    relationships.seed_family(state)

    state.feed.append(FeedEntry(
        age=0,
        text=f"You were born in {country}. You are a {gender.lower()}.",
        kind="special",
        entry_id=f"feed:birth:{uuid.uuid4().hex[:8]}",
    ))
    return state


def age_up(state: GameState) -> None:
    """Advance one year. Mutates state in place."""
    if state.mode != "PLAYING" or state.character is None:
        return
    if state.pending_event_id is not None:
        # Player must resolve the pending event first.
        return

    state.tick += 1
    state.character.age += 1
    age = state.character.age
    tick_rng = Rng(state.seed).fork(state.tick)

    summary_parts: list[str] = [f"You are now {age} years old."]

    # --- Education lifecycle ---
    edu_msg = education.tick(state)
    if edu_msg:
        summary_parts.append(edu_msg)

    # --- Economy ---
    if age >= 18:
        earnings, living_cost, note = economy.annual_cashflow(state, tick_rng.fork(7))
        if note:
            summary_parts.append(note)
        state.money += earnings - living_cost
        if state.money < 0:
            summary_parts.append("You are in debt.")
            state.stats.happiness -= 10
            state.stats.health -= 5
        if not state.career:
            state.stats.happiness -= 5

    # --- Natural drift ---
    if age > 50:
        state.stats.health -= tick_rng.fork(11).randint(0, 5)
    state.stats.happiness -= tick_rng.fork(13).randint(0, 3)
    relationships.annual_drift(state)
    state.stats = state.stats.clamped()

    # --- Feed entry for the year ---
    state.feed.append(FeedEntry(
        age=age,
        text=" ".join(summary_parts),
        kind="neutral",
        entry_id=f"feed:annual:{state.tick}",
    ))

    # --- Death check ---
    death_age_threshold = 100 + tick_rng.fork(17).randint(0, 10)
    if state.stats.health <= 0 or age > death_age_threshold:
        state.character.alive = False
        state.mode = "DEATH"
        state.feed.append(FeedEntry(
            age=age,
            text="You have passed away.",
            kind="bad",
            entry_id=f"feed:death:{state.tick}",
        ))
        return

    # --- Roll for a random event ---
    event = events.roll_event(state, tick_rng.fork(23))
    if event is not None:
        state.pending_event_id = event["id"]


def resolve_choice(state: GameState, choice_index: int) -> None:
    if state.pending_event_id is None:
        return
    events.resolve_choice(state, state.pending_event_id, choice_index)


def get_pending_event(state: GameState) -> dict | None:
    if state.pending_event_id is None:
        return None
    return events.get_event(state.pending_event_id)
