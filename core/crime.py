"""Crime v1 — commit a crime, roll for arrest, do time, carry a record.

State machine
-------------

::

    clean ──attempt_crime──▶ success (money +)
                       └──▶ arrest ──▶ incarcerated ──serve N years──▶ released
                                                                          │
                                                          past_offences ◀─┘

Determinism
-----------

All randomness goes through a forked Rng (callers pass one in). Same
seed + same attempt sequence -> same outcomes.

Where state lives
-----------------

- ``state.crime`` (CriminalRecord) carries the flag + counters + record.
- ``state.pending_crime_outcome`` is the modal payload the UI raises
  after each attempt: a dict with title / text / caught / payout. The
  ``acknowledge_crime_outcome`` controller verb clears it.

Coexistence with the rest of the sim
------------------------------------

When ``is_incarcerated`` is True:
  - sim.age_up skips the standard career/education/economy/social ticks
    and runs ``prison_tick`` instead (defined here).
  - The event engine filters its candidate pool to only events with an
    ``IsIncarcerated`` predicate, so the catalogue's 100+ free-world
    events don't fire absurdly ("you went to the office party — from
    your cell?").
  - The controller refuses normal activity verbs (study/gym/date/etc.)
    with a "you're in prison" log line.

After release, ``crime.past_offences`` survives. ``HasCriminalRecord``
predicate gates events that should react to a felony in the player's
past (cold-shoulder from employer, parole-officer visits).
"""
from __future__ import annotations

from typing import Optional

from core.rng import Rng
from core.state import FeedEntry, GameState


# Each crime: a fixed declarative recipe the UI can list, the engine can
# resolve, and tests can assert against. Lifted from the architectural
# blueprint, expanded to a tighter ladder of risk vs payout.
CRIME_CATALOGUE: dict[str, dict] = {
    "pickpocket": {
        "name": "Pickpocketing",
        "min_age": 12, "base_success": 0.78,
        "payout_min": 5, "payout_max": 60,
        "sentence_years": 1,
        "stat_modifier": "smarts",
        "blurb": "Lift a wallet in a crowd. Low risk, low reward.",
    },
    "shoplift": {
        "name": "Shoplifting",
        "min_age": 12, "base_success": 0.72,
        "payout_min": 10, "payout_max": 120,
        "sentence_years": 1,
        "stat_modifier": "smarts",
        "blurb": "Walk out with what you didn't pay for.",
    },
    "vandalism": {
        "name": "Vandalism",
        "min_age": 12, "base_success": 0.80,
        "payout_min": 0, "payout_max": 0,
        "sentence_years": 1,
        "stat_modifier": "health",
        "blurb": "Spray paint, smashed windows. No payout, just bile.",
    },
    "burglary": {
        "name": "Burglary",
        "min_age": 16, "base_success": 0.55,
        "payout_min": 500, "payout_max": 5_000,
        "sentence_years": 3,
        "stat_modifier": "smarts",
        "blurb": "Empty house, full pockets. Riskier than it sounds.",
    },
    "fraud": {
        "name": "Wire Fraud",
        "min_age": 18, "base_success": 0.50,
        "payout_min": 1_000, "payout_max": 20_000,
        "sentence_years": 4,
        "stat_modifier": "smarts",
        "blurb": "A long con played over email. Pays well; sentences long.",
    },
    "grand_theft_auto": {
        "name": "Grand Theft Auto",
        "min_age": 18, "base_success": 0.40,
        "payout_min": 5_000, "payout_max": 30_000,
        "sentence_years": 5,
        "stat_modifier": "health",
        "blurb": "Drive away in something that isn't yours.",
    },
    "bank_heist": {
        "name": "Bank Heist",
        "min_age": 21, "base_success": 0.18,
        "payout_min": 50_000, "payout_max": 250_000,
        "sentence_years": 15,
        "stat_modifier": "smarts",
        "blurb": "The one big score. The fall is just as big.",
    },
}


def list_crimes_for_ui(state: GameState) -> list[dict]:
    """JSON-friendly view of the catalogue with computed success chance.
    Each entry includes an ``available`` flag so the UI can grey out crimes
    the player is too young for or already in prison from attempting."""
    out: list[dict] = []
    incarcerated = state.crime.is_incarcerated
    age = state.character.age if state.character else 0
    for crime_id, crime in CRIME_CATALOGUE.items():
        ok_age = age >= crime["min_age"]
        out.append({
            "id": crime_id,
            "name": crime["name"],
            "blurb": crime["blurb"],
            "min_age": crime["min_age"],
            "payout_range": [crime["payout_min"], crime["payout_max"]],
            "sentence_years": crime["sentence_years"],
            "success_chance": round(_compute_success_chance(state, crime), 2),
            "available": ok_age and not incarcerated,
        })
    return out


def _compute_success_chance(state: GameState, crime: dict) -> float:
    """Base chance plus up to +0.20 if the relevant stat is maxed.
    Capped at 0.95 so even bank heists can plausibly go wrong."""
    base = crime["base_success"]
    stat_value = getattr(state.stats, crime["stat_modifier"], 50)
    bonus = (stat_value / 100.0) * 0.20
    return min(0.95, base + bonus)


def attempt_crime(state: GameState, crime_id: str, rng: Rng) -> dict:
    """Roll the outcome of a crime attempt, mutate state, and return the
    modal payload (title / text / caught / payout). Refuses cleanly when:
      - crime_id is unknown
      - the player is already incarcerated
      - the player is below the crime's min_age

    The payload is also written to ``state.pending_crime_outcome`` so the
    UI's modal layer can read it via the snapshot. On a clean refusal,
    that field is set to a {caught:false, payout:0, refused:true} payload
    instead of mutating money/state — callers can rely on a payload
    always being returned for refused/ok/caught alike.
    """
    crime = CRIME_CATALOGUE.get(crime_id)
    if crime is None:
        payload = {"ok": False, "refused": True,
                   "title": "Unknown crime",
                   "text": "That isn't in the playbook.",
                   "caught": False, "payout": 0}
        state.pending_crime_outcome = payload
        return payload

    if state.character is None or not state.character.alive:
        return {"ok": False, "refused": True,
                "title": "Not now", "text": "You can't commit a crime right now.",
                "caught": False, "payout": 0}

    if state.crime.is_incarcerated:
        payload = {"ok": False, "refused": True,
                   "title": "You're already inside",
                   "text": "You can't very well rob a bank from a cell.",
                   "caught": False, "payout": 0}
        state.pending_crime_outcome = payload
        return payload

    if state.character.age < crime["min_age"]:
        payload = {"ok": False, "refused": True,
                   "title": "Too young",
                   "text": f"{crime['name']} isn't an option for you yet.",
                   "caught": False, "payout": 0}
        state.pending_crime_outcome = payload
        return payload

    chance = _compute_success_chance(state, crime)
    if rng.fork(1).chance(chance):
        # Clean getaway
        payout = rng.fork(2).randint(crime["payout_min"], crime["payout_max"])
        state.money += payout
        # Successful crimes still leave a small happiness bump (adrenaline)
        # and a tiny health hit (stress). Vandalism with zero payout still
        # registers as 'something happened'.
        state.stats.happiness = min(100, state.stats.happiness + 4)
        success_text = (
            f"You pulled off {crime['name']} and walked away £{payout:,} richer."
            if payout > 0 else
            f"You pulled off {crime['name']} and walked away clean."
        )
        payload = {
            "ok": True, "caught": False, "payout": payout,
            "crime_id": crime_id, "name": crime["name"],
            "title": "Clean Getaway",
            "text": success_text,
        }
        state.pending_crime_outcome = payload
        state.feed.append(FeedEntry(
            age=state.character.age,
            text=success_text, kind="special",
            entry_id=f"feed:crime_success:{state.tick}:{crime_id}",
        ))
        return payload

    # Caught and convicted
    sentence = crime["sentence_years"]
    state.crime.is_incarcerated = True
    state.crime.sentence_years = sentence
    state.crime.years_served = 0
    state.crime.past_offences.append(crime["name"])

    # Immediate cascade: lose job, drop out of school, big happiness hit.
    # Education level stays (you don't forget your degree) — only enrolment
    # ends.
    state.career = None
    state.education.in_school = False
    state.education.degree_award_pending = False
    state.education.awaiting_university_choice = False
    state.stats.happiness = max(0, state.stats.happiness - 60)
    # Active romance arcs end on arrest (your partner can't visit weekly
    # from a cell in the way the sim models). Dating prospect clears;
    # Partner stays put as a Relationship — they may stick by you or
    # leave through normal channels later.
    state.dating = None
    # Pending pregnancy stays; that's biology, not legal status.

    caught_text = (
        f"The police caught you. {crime['name']} — {sentence} year"
        f"{'s' if sentence != 1 else ''} inside."
    )
    payload = {
        "ok": True, "caught": True, "payout": 0,
        "crime_id": crime_id, "name": crime["name"],
        "title": "Busted",
        "text": caught_text,
        "sentence_years": sentence,
    }
    state.pending_crime_outcome = payload
    state.feed.append(FeedEntry(
        age=state.character.age,
        text=caught_text, kind="bad",
        entry_id=f"feed:crime_caught:{state.tick}:{crime_id}",
    ))
    return payload


# --- Prison tick + release -----------------------------------------------


def prison_tick(state: GameState) -> Optional[str]:
    """Advance one year of incarceration. Called from sim.age_up while
    is_incarcerated is True. Returns a one-line summary for the year
    (or None if no character).

    On the year sentence_years is reached, this releases the player:
    flips is_incarcerated off, zeroes the counters, returns a release
    summary. Past offences stay on past_offences forever.
    """
    if state.character is None or not state.crime.is_incarcerated:
        return None
    state.crime.years_served += 1
    if state.crime.years_served >= state.crime.sentence_years:
        # Release. Counters zero; record stays.
        served = state.crime.years_served
        state.crime.is_incarcerated = False
        state.crime.sentence_years = 0
        state.crime.years_served = 0
        # Modest reset — released with health damage, low happiness, but
        # not catastrophic. The struggle to rebuild is the rest of the
        # arc, not a stat tax.
        state.stats.happiness = min(100, state.stats.happiness + 20)
        msg = f"You walked out a free person after {served} year{'s' if served != 1 else ''} inside."
    else:
        # Year of incarceration. Light stat drift — institutionalisation,
        # boredom, fights. Smarts can creep up if the player took prison
        # classes (modelled as a small per-year bump).
        state.stats.health = max(0, state.stats.health - 1)
        state.stats.happiness = max(0, state.stats.happiness - 2)
        state.stats.smarts = min(100, state.stats.smarts + 1)
        remaining = state.crime.sentence_years - state.crime.years_served
        msg = f"Year {state.crime.years_served} inside. {remaining} to go."
    state.feed.append(FeedEntry(
        age=state.character.age,
        text=msg,
        kind="bad" if state.crime.is_incarcerated else "good",
        entry_id=f"feed:prison:{state.tick}",
    ))
    return msg
