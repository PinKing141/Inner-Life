"""Core simulation tick.

This is the only place that 'a year passes' for the player. Anything that
should happen yearly — economy, education, NPC drift, random events, death
checks — runs from here, in a fixed order.

Determinism rule: given the same GameState and same Rng, calling `age_up`
must produce identical results every time.
"""
from __future__ import annotations

import uuid

from core import agents, economy, education, events, relationships, social, world
from core.content import countries as countries_mod
from core.content import names as names_mod
from core.rng import Rng
from core.state import Character, FeedEntry, GameState, Stats

CONCEPTION_STORIES = [
    "an unplanned pregnancy after a late-night party",
    "a honeymoon surprise",
    "a planned pregnancy after months of trying",
    "a spontaneous road-trip weekend",
    "a backseat-of-a-car mistake after a concert",
    "a reunion after years apart",
    "a New Year's Eve celebration that got out of hand",
    "a vacation fling that became serious",
    "a deliberate IVF cycle",
    "an IUI treatment at a fertility clinic",
    "a donor conception arranged through a clinic",
    "a one-night stand that changed everything",
    "a college romance that lasted just long enough",
    "a whirlwind workplace romance",
    "a reconciled relationship after a breakup",
    "a festival weekend hookup",
    "a planned second child conversation",
    "an accidental missed birth-control week",
    "a post-wedding celebration surprise",
    "a long-distance visit that turned lucky",
    "a hopeful 'let's see what happens' month",
    "a cabin getaway during winter break",
    "a carefully tracked ovulation plan",
    "a surprise after doctors said it was unlikely",
    "a friends-to-lovers turning point",
    "a dating-app match that moved fast",
    "a family-planned adoption path",
    "a surrogate journey",
    "a spring-break romance",
    "a music-festival weekend",
    "a city blackout candlelit night",
    "a proposal-night celebration",
]

PARENT_JOBS = [
    "Nurse", "Teacher", "Retail Manager", "Software Engineer", "Delivery Driver",
    "Electrician", "Chef", "Accountant", "Police Officer", "Mechanic",
    "Sales Representative", "Graphic Designer", "Pharmacist", "Truck Driver",
    "Construction Worker", "Real Estate Agent", "HR Specialist", "Barber",
    "Dentist", "Plumber",
]

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
    mother_first = names_mod.random_forename(country_info.code, "Female", rng.fork(41))
    father_first = names_mod.random_forename(country_info.code, "Male", rng.fork(42))
    mother_age = rng.fork(43).randint(20, 45)
    father_age = rng.fork(44).randint(20, 50)
    mother_job = rng.fork(45).choice(PARENT_JOBS)
    father_job = rng.fork(46).choice(PARENT_JOBS)
    mother_name = f"{mother_first} {last_name}".strip()
    father_name = f"{father_first} {last_name}".strip()
    lineage_id = f"{country_info.code.lower()}-{last_name.lower()}-{seed % 10_000}"
    birth_story = rng.fork(47).choice(CONCEPTION_STORIES)
    parent_details = [
        {"name": mother_name, "role": "Mother", "age_at_birth": mother_age, "job": mother_job},
        {"name": father_name, "role": "Father", "age_at_birth": father_age, "job": father_job},
    ]

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

    starting_wealth = 0

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
            parents=[1, 2],
            children=[],
            lineage_id=lineage_id,
            birth_story=birth_story,
            parent_details=parent_details,
        ),
        stats=Stats(
            happiness=100,
            health=min(100, base_health),
            smarts=min(100, base_smarts),
            looks=min(100, base_looks),
        ),
        money=starting_wealth,
    )
    relationships.seed_family(state, rng.fork(101), mother_name=mother_name, father_name=father_name)
    agents.seed_world(state, rng.fork(202))

    state.feed.append(FeedEntry(
        age=0,
        text=(
            f"You were born in {city}, {country_info.name}. You are a {gender.lower()}. "
            f"You were conceived through {birth_story}. "
            f"Your mother is {mother_name}, age {mother_age}, working as a {mother_job}. "
            f"Your father is {father_name}, age {father_age}, working as a {father_job}."
        ),
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

    # --- Macro world tick (Phase 4A) ---
    world.tick_world(state, tick_rng.fork(29))

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

    # --- Career progression (promotions) ---
    promotion = economy.career_tick(state, tick_rng.fork(8))
    if promotion is not None:
        state.pending_promotion = promotion
        summary_parts.append(
            f"You were promoted to {promotion['title']} (+{promotion['pct']}%)."
        )

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
