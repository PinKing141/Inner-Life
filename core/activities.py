"""Canonical activity effects — the single source of truth for what each
player verb (study, gym, doctor, hang out, vacation, …) does to a character.

Both the controller (real player actions) and the headless auto-play policy
used by the observatory call these, so there is no second copy of the numbers
to drift. Each returns ``(ok, log)``; state is mutated only as described.

When an activity is gated (cost, age, living relative, education) it returns
``(False, reason)`` instead of mutating — the controller logs the reason as
a feed entry so the player sees *why* the tap didn't work.
"""
from __future__ import annotations

from core import relationships
from core.state import GameState, Relationship

# --- Costs (single source of truth so descriptors and effects can't drift) -

GYM_COST = 30
DOCTOR_COST = 100
THERAPY_COST = 40
HAIRCUT_COST = 20
TATTOO_COST = 80
COSMETIC_COST = 5_000
VACATION_COST = 1_500
PARTY_COST = 200
BAR_COST = 40
DIET_COST = 20
SPA_COST = 150
DATE_NIGHT_COST = 100

# --- Unlock ages (exposed via descriptors so the UI greys out locked rows) -

STUDY_MIN_AGE = 5
GYM_MIN_AGE = 12
DOCTOR_MIN_AGE = 0
FAMILY_TIME_MIN_AGE = 0
MEDITATE_MIN_AGE = 8
READ_MIN_AGE = 6
THERAPY_MIN_AGE = 12
HAIRCUT_MIN_AGE = 3
TATTOO_MIN_AGE = 16
COSMETIC_MIN_AGE = 18
VACATION_MIN_AGE = 18
PARK_MIN_AGE = 3
CALL_PARENT_MIN_AGE = 8
DATE_NIGHT_MIN_AGE = 18
HANG_FRIENDS_MIN_AGE = 6
PARTY_MIN_AGE = 16
BAR_MIN_AGE = 18
JOG_MIN_AGE = 8
DIET_MIN_AGE = 12
VOLUNTEER_MIN_AGE = 12
SIDE_GIG_MIN_AGE = 16
SPA_MIN_AGE = 14


# --- Helpers ---------------------------------------------------------------


def _clamp(value: int, lo: int = 0, hi: int = 100) -> int:
    return max(lo, min(hi, value))


def _age(state: GameState) -> int:
    return state.character.age if state.character else 0


def _first_living(state: GameState, kind: str) -> Relationship | None:
    return next((r for r in state.relationships if r.kind == kind and r.alive), None)


def _bump_relationship(rel: Relationship, delta: int) -> None:
    rel.relationship = _clamp(rel.relationship + delta)


# --- Existing four ---------------------------------------------------------


def study(state: GameState) -> tuple[bool, str]:
    state.stats.smarts = _clamp(state.stats.smarts + 2)
    state.stats.happiness = _clamp(state.stats.happiness - 2)
    return True, "You studied hard. You feel smarter, but a bit bored."


def gym(state: GameState) -> tuple[bool, str]:
    if state.money < GYM_COST:
        return False, "You cannot afford the gym."
    state.money -= GYM_COST
    state.stats.health = _clamp(state.stats.health + 3)
    state.stats.looks = _clamp(state.stats.looks + 1)
    return True, "You went to the gym. It cost £30."


def school_nurse(state: GameState) -> tuple[bool, str]:
    """Free clinic visit at school — small health bump, no cost.
    Only useful while in school (the controller / UI gates this), but
    the activity itself doesn't care; the engine is permissive."""
    state.stats.health = min(100, state.stats.health + 5)
    return True, "You went to the school nurse. Quick rest, plaster on, sent back."


def doctor(state: GameState) -> tuple[bool, str]:
    if state.money < DOCTOR_COST:
        return False, "You cannot afford a private doctor."
    state.money -= DOCTOR_COST
    state.stats.health = _clamp(state.stats.health + 15)
    return True, "You visited a private doctor. It cost £100 but you feel much better."


def family_time(state: GameState) -> tuple[bool, str]:
    relationships.spend_time_with_family(state)
    state.stats.happiness = _clamp(state.stats.happiness + 5)
    return True, "You spent quality time with your family."


# --- Mind & wellbeing -----------------------------------------------------


def meditate(state: GameState) -> tuple[bool, str]:
    state.stats.happiness = _clamp(state.stats.happiness + 3)
    state.stats.health = _clamp(state.stats.health + 1)
    return True, "You sat in stillness for a while. Your mind feels clearer."


def read_book(state: GameState) -> tuple[bool, str]:
    state.stats.smarts = _clamp(state.stats.smarts + 1)
    state.stats.happiness = _clamp(state.stats.happiness + 2)
    return True, "You read a book. A small expansion of your inner world."


def therapy(state: GameState) -> tuple[bool, str]:
    if state.money < THERAPY_COST:
        return False, "You cannot afford a therapy session."
    state.money -= THERAPY_COST
    state.stats.happiness = _clamp(state.stats.happiness + 8)
    return True, "You talked to a therapist. Something heavy lifted, a little. £40."


def walk_in_park(state: GameState) -> tuple[bool, str]:
    state.stats.happiness = _clamp(state.stats.happiness + 2)
    state.stats.health = _clamp(state.stats.health + 1)
    return True, "You walked in the park. Birds, sunlight, the usual."


# --- Looks ----------------------------------------------------------------


def haircut(state: GameState) -> tuple[bool, str]:
    if state.money < HAIRCUT_COST:
        return False, "You cannot afford a haircut today."
    state.money -= HAIRCUT_COST
    state.stats.looks = _clamp(state.stats.looks + 2)
    state.stats.happiness = _clamp(state.stats.happiness + 1)
    return True, "You got a fresh haircut. People will notice. £20."


def tattoo(state: GameState) -> tuple[bool, str]:
    if state.money < TATTOO_COST:
        return False, "You cannot afford the tattoo."
    state.money -= TATTOO_COST
    # Looks is subjective — small +. Happiness up either way: you have a tattoo now.
    state.stats.looks = _clamp(state.stats.looks + 1)
    state.stats.happiness = _clamp(state.stats.happiness + 3)
    return True, "You got a tattoo. It's permanent, like every decision. £80."


def cosmetic_surgery(state: GameState) -> tuple[bool, str]:
    if state.money < COSMETIC_COST:
        return False, "You cannot afford cosmetic surgery."
    state.money -= COSMETIC_COST
    state.stats.looks = _clamp(state.stats.looks + 10)
    state.stats.health = _clamp(state.stats.health - 3)  # recovery toll
    return True, "You had cosmetic work done. The bruising fades. £5,000."


def spa_day(state: GameState) -> tuple[bool, str]:
    if state.money < SPA_COST:
        return False, "You cannot afford a spa day."
    state.money -= SPA_COST
    state.stats.happiness = _clamp(state.stats.happiness + 5)
    state.stats.looks = _clamp(state.stats.looks + 2)
    return True, "You spent the day at a spa. You forgot what tension felt like. £150."


# --- Body / health --------------------------------------------------------


def jog(state: GameState) -> tuple[bool, str]:
    state.stats.health = _clamp(state.stats.health + 2)
    state.stats.happiness = _clamp(state.stats.happiness + 1)
    return True, "You went for a jog. Your legs hurt; you feel virtuous."


def healthy_diet(state: GameState) -> tuple[bool, str]:
    if state.money < DIET_COST:
        return False, "You cannot afford the better food right now."
    state.money -= DIET_COST
    state.stats.health = _clamp(state.stats.health + 2)
    return True, "You ate well this week. Your body thanks you quietly. £20."


def party(state: GameState) -> tuple[bool, str]:
    if state.money < PARTY_COST:
        return False, "You cannot afford to throw a party."
    state.money -= PARTY_COST
    state.stats.happiness = _clamp(state.stats.happiness + 8)
    state.stats.health = _clamp(state.stats.health - 3)
    return True, "You threw a party. People came; people left; it was great. £200."


def night_at_the_bar(state: GameState) -> tuple[bool, str]:
    if state.money < BAR_COST:
        return False, "You cannot afford a night out at the bar."
    state.money -= BAR_COST
    state.stats.happiness = _clamp(state.stats.happiness + 5)
    state.stats.health = _clamp(state.stats.health - 2)
    return True, "You spent a few hours at a loud bar. Your liver disapproves. £40."


# --- Social ---------------------------------------------------------------


def call_mother(state: GameState) -> tuple[bool, str]:
    mum = _first_living(state, "Mother")
    if mum is None:
        return False, "Your mother isn't around to call."
    _bump_relationship(mum, 4)
    state.stats.happiness = _clamp(state.stats.happiness + 3)
    return True, f"You rang {mum.name}. She was glad to hear from you."


def call_father(state: GameState) -> tuple[bool, str]:
    dad = _first_living(state, "Father")
    if dad is None:
        return False, "Your father isn't around to call."
    _bump_relationship(dad, 4)
    state.stats.happiness = _clamp(state.stats.happiness + 3)
    return True, f"You rang {dad.name}. He kept it short, the way he does."


def hang_with_friends(state: GameState) -> tuple[bool, str]:
    friend = _first_living(state, "Friend")
    if friend is None:
        return False, "You don't have any friends to call right now."
    _bump_relationship(friend, 3)
    state.stats.happiness = _clamp(state.stats.happiness + 4)
    return True, f"You spent the evening with {friend.name}."


def date_night(state: GameState) -> tuple[bool, str]:
    partner = _first_living(state, "Partner")
    if partner is None:
        return False, "You don't have a partner for a date night."
    if state.money < DATE_NIGHT_COST:
        return False, "You cannot afford the date night you had in mind."
    state.money -= DATE_NIGHT_COST
    _bump_relationship(partner, 5)
    state.stats.happiness = _clamp(state.stats.happiness + 5)
    return True, f"A proper night out with {partner.name}. Worth every pound. £100."


# --- Productive / financial ----------------------------------------------


def volunteer(state: GameState) -> tuple[bool, str]:
    state.stats.happiness = _clamp(state.stats.happiness + 4)
    state.stats.smarts = _clamp(state.stats.smarts + 1)
    return True, "You volunteered with a local cause. It felt like doing something."


def side_gig(state: GameState) -> tuple[bool, str]:
    # Deterministic small earn — keeps the activity reliable for budgeting.
    state.money += 60
    state.stats.happiness = _clamp(state.stats.happiness - 2)
    return True, "You picked up a few hours of side work. Earned £60."


def vacation(state: GameState) -> tuple[bool, str]:
    if state.money < VACATION_COST:
        return False, "You cannot afford a vacation right now."
    state.money -= VACATION_COST
    state.stats.happiness = _clamp(state.stats.happiness + 15)
    state.stats.health = _clamp(state.stats.health + 3)
    return True, "You took a real vacation. The world felt larger when you got back. £1,500."


# --- Dispatch table -------------------------------------------------------


# Verb name (as the UI/bridge uses) -> effect function.
BY_KIND = {
    "study": study,
    "gym": gym,
    "doctor": doctor,
    "school_nurse": school_nurse,
    "spend_time": family_time,
    "meditate": meditate,
    "read_book": read_book,
    "therapy": therapy,
    "walk_in_park": walk_in_park,
    "haircut": haircut,
    "tattoo": tattoo,
    "cosmetic_surgery": cosmetic_surgery,
    "spa_day": spa_day,
    "jog": jog,
    "healthy_diet": healthy_diet,
    "party": party,
    "night_at_the_bar": night_at_the_bar,
    "call_mother": call_mother,
    "call_father": call_father,
    "hang_with_friends": hang_with_friends,
    "date_night": date_night,
    "volunteer": volunteer,
    "side_gig": side_gig,
    "vacation": vacation,
}


# UI descriptors — read by the controller into the snapshot so the front-end
# can render the Activities screen without inventing its own copy of the data.
# Grouped by category in declaration order so the UI renders sensibly.
DESCRIPTORS = [
    # Health / body
    {"id": "doctor", "title": "Visit the Doctor",
     "subtitle": f"A check-up — costs £{DOCTOR_COST}.",
     "unlock": DOCTOR_MIN_AGE, "icon": "doctor", "accent": "health"},
    {"id": "gym", "title": "Go to the Gym",
     "subtitle": f"Train for health and looks — £{GYM_COST}.",
     "unlock": GYM_MIN_AGE, "icon": "dumbbell", "accent": "health"},
    {"id": "jog", "title": "Go Jogging",
     "subtitle": "Free, sweaty, surprisingly virtuous.",
     "unlock": JOG_MIN_AGE, "icon": "shoe", "accent": "health"},
    {"id": "healthy_diet", "title": "Eat Healthier",
     "subtitle": f"Better food, slowly better body — £{DIET_COST}.",
     "unlock": DIET_MIN_AGE, "icon": "apple", "accent": "health"},
    # Mind
    {"id": "study", "title": "Study Hard",
     "subtitle": "Boost your smarts; a little bored.",
     "unlock": STUDY_MIN_AGE, "icon": "book", "accent": "smarts"},
    {"id": "read_book", "title": "Read a Book",
     "subtitle": "A quiet hour. Smarts and happiness, both up a touch.",
     "unlock": READ_MIN_AGE, "icon": "book", "accent": "smarts"},
    {"id": "meditate", "title": "Meditate",
     "subtitle": "Sit. Breathe. Try not to plan dinner.",
     "unlock": MEDITATE_MIN_AGE, "icon": "lotus", "accent": "happy"},
    {"id": "therapy", "title": "See a Therapist",
     "subtitle": f"A real session — £{THERAPY_COST}.",
     "unlock": THERAPY_MIN_AGE, "icon": "speech", "accent": "happy"},
    # Looks
    {"id": "haircut", "title": "Get a Haircut",
     "subtitle": f"Fresh fade — £{HAIRCUT_COST}.",
     "unlock": HAIRCUT_MIN_AGE, "icon": "scissors", "accent": "looks"},
    {"id": "spa_day", "title": "Spa Day",
     "subtitle": f"Hot stones, soft towels — £{SPA_COST}.",
     "unlock": SPA_MIN_AGE, "icon": "spa", "accent": "looks"},
    {"id": "tattoo", "title": "Get a Tattoo",
     "subtitle": f"Ink that means something — £{TATTOO_COST}.",
     "unlock": TATTOO_MIN_AGE, "icon": "needle", "accent": "looks"},
    {"id": "cosmetic_surgery", "title": "Cosmetic Surgery",
     "subtitle": f"A serious procedure — £{COSMETIC_COST:,}.",
     "unlock": COSMETIC_MIN_AGE, "icon": "scalpel", "accent": "looks"},
    # Social
    {"id": "spend_time", "title": "Spend Time with Family",
     "subtitle": "Strengthen bonds with relatives.",
     "unlock": FAMILY_TIME_MIN_AGE, "icon": "heart", "accent": "happy"},
    {"id": "call_mother", "title": "Call Mum",
     "subtitle": "A few minutes on the phone.",
     "unlock": CALL_PARENT_MIN_AGE, "icon": "phone", "accent": "happy"},
    {"id": "call_father", "title": "Call Dad",
     "subtitle": "He'll keep it brief.",
     "unlock": CALL_PARENT_MIN_AGE, "icon": "phone", "accent": "happy"},
    {"id": "hang_with_friends", "title": "Hang with Friends",
     "subtitle": "Cheaper than therapy. Sometimes.",
     "unlock": HANG_FRIENDS_MIN_AGE, "icon": "users", "accent": "happy"},
    {"id": "date_night", "title": "Date Night",
     "subtitle": f"With your partner — £{DATE_NIGHT_COST}.",
     "unlock": DATE_NIGHT_MIN_AGE, "icon": "heart", "accent": "happy"},
    # Leisure
    {"id": "walk_in_park", "title": "Walk in the Park",
     "subtitle": "Free. Restorative. Light on the knees.",
     "unlock": PARK_MIN_AGE, "icon": "tree", "accent": "happy"},
    {"id": "party", "title": "Throw a Party",
     "subtitle": f"Big night — £{PARTY_COST}.",
     "unlock": PARTY_MIN_AGE, "icon": "balloons", "accent": "happy"},
    {"id": "night_at_the_bar", "title": "Night at the Bar",
     "subtitle": f"Loud, sticky, fun — £{BAR_COST}.",
     "unlock": BAR_MIN_AGE, "icon": "glass", "accent": "happy"},
    {"id": "vacation", "title": "Take a Vacation",
     "subtitle": f"A proper trip — £{VACATION_COST:,}.",
     "unlock": VACATION_MIN_AGE, "icon": "palm", "accent": "happy"},
    # Productive
    {"id": "volunteer", "title": "Volunteer",
     "subtitle": "Do something for someone else. Free.",
     "unlock": VOLUNTEER_MIN_AGE, "icon": "hands", "accent": "happy"},
    {"id": "side_gig", "title": "Pick Up a Side Gig",
     "subtitle": "Trade a little happiness for £60.",
     "unlock": SIDE_GIG_MIN_AGE, "icon": "briefcase", "accent": "money"},
]


def list_descriptors() -> list[dict]:
    return [dict(d) for d in DESCRIPTORS]
