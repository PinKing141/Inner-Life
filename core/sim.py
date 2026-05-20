"""Core simulation tick.

This is the only place that 'a year passes' for the player. Anything that
should happen yearly — economy, education, NPC drift, random events, death
checks — runs from here, in a fixed order.

Determinism rule: given the same GameState and same Rng, calling `age_up`
must produce identical results every time.
"""
from __future__ import annotations

import uuid

from core import agents, economy, education, events, relationships, social
from core.content import countries as countries_mod
from core.content import names as names_mod
from core.rng import Rng
from core.state import Character, FeedEntry, GameState, Stats


def _split_name(full: str) -> tuple[str, str]:
    parts = (full or "").strip().split(maxsplit=1)
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[1]


def new_game(
    seed: int,
    name: str,
    gender: str,
    country: str,
    talent: str,
    *,
    first_name: str | None = None,
    last_name: str | None = None,
    city: str | None = None,
) -> GameState:
    """Initialise a fresh life. Stats are biased by talent.

    Either pass `name` (legacy) or `first_name` + `last_name`. Anything blank
    is filled with a country-aware random pick so the character always has a
    plausible local-sounding name.
    """
    rng = Rng(seed)

    # --- Resolve the country & city ---
    country_info = countries_mod.resolve(country)
    if city is None or not city:
        city = country_info.cities[0]
    elif city not in country_info.cities:
        # Out-of-list city is allowed — players can type something custom.
        city = city.strip() or country_info.cities[0]

    # --- Resolve names ---
    if first_name is None and last_name is None:
        first_name, last_name = _split_name(name)
    if not first_name:
        first_name = names_mod.random_forename(country_info.code, gender, rng)
    if not last_name:
        last_name = names_mod.random_surname(country_info.code, rng)

    # --- Stat rolls ---
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
        character=Character(
            first_name=first_name,
            last_name=last_name,
            gender=gender,
            country=country_info.name,
            city=city,
            talent=talent,
            age=0,
        ),
        stats=Stats(
            happiness=100,
            health=min(100, base_health),
            smarts=min(100, base_smarts),
            looks=min(100, base_looks),
        ),
        money=starting_wealth,
    )
    relationships.seed_family(state, rng.fork(101))
    agents.seed_world(state, rng.fork(202))

    state.feed.append(FeedEntry(
        age=0,
        text=f"You were born in {city}, {country_info.name}. You are a {gender.lower()}.",
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

    # --- NPC world tick (Phase 1 — parents and friends age too) ---
    agents.tick_world(state, tick_rng.fork(31))
    social.tick_social(state, tick_rng.fork(33))

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
