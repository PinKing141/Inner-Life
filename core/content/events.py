"""Random life events.

Each event is data. Effects, choices, age windows, probabilities — all
declared here. The event engine (core.events) reads from this list and never
encodes individual events itself.

To add a new event: append a dict here. No engine changes needed.
"""
from __future__ import annotations

# Each "choice" maps to: text shown to player, stat/money effects, log line.
# The `log` is what gets written to the feed; the `text` is the question.

EVENTS: list[dict] = [
    {
        "id": "first_word",
        "min_age": 1, "max_age": 2, "prob": 0.8,
        "text": "You are trying to speak your first word.",
        "choices": [
            {"text": "Say 'Mum'", "effects": {"happiness": 5, "smarts": 2},
             "log": "You said 'Mum'. Your parents clapped in delight."},
            {"text": "Say 'Dad'", "effects": {"happiness": 5, "smarts": 2},
             "log": "You said 'Dad'. Your parents smiled warmly."},
            {"text": "Scream instead", "effects": {"happiness": -2, "smarts": -2},
             "log": "You just screamed. Your parents looked exhausted."},
        ],
    },
    {
        "id": "nursery_bully",
        "min_age": 4, "max_age": 6, "prob": 0.3,
        "text": "A bigger child at nursery tries to steal your favourite toy.",
        "choices": [
            {"text": "Give it to them", "effects": {"happiness": -10, "smarts": 5},
             "log": "You gave up the toy to avoid trouble. You felt a bit sad."},
            {"text": "Bite them", "effects": {"health": -5, "happiness": 5, "looks": -2},
             "log": "You bit the child. You kept your toy but got told off."},
            {"text": "Cry loudly", "effects": {"happiness": -5, "smarts": -5},
             "log": "You cried until the nursery nurse intervened."},
        ],
    },
    {
        "id": "primary_school_test",
        "min_age": 8, "max_age": 11, "prob": 0.4,
        "text": "You have a surprise Maths test today in Primary School.",
        "choices": [
            {"text": "Try your best", "effects": {"smarts": 5, "happiness": -2},
             "log": "You focused hard and did well on the test."},
            {"text": "Cheat off a friend", "effects": {"smarts": -5, "happiness": -5},
             "log": "You were caught cheating and sent to the Headteacher."},
            {"text": "Doodle on the paper", "effects": {"smarts": -2, "happiness": 5},
             "log": "You drew a lovely picture of a dinosaur instead of doing maths."},
        ],
    },
    {
        "id": "teen_party",
        "min_age": 14, "max_age": 17, "prob": 0.3,
        "text": "You have been invited to a house party, but it is on a school night.",
        "choices": [
            {"text": "Sneak out and go", "effects": {"happiness": 15, "smarts": -10, "health": -5},
             "log": "You snuck out. It was amazing, but you fell asleep in class the next day."},
            {"text": "Stay home and study", "effects": {"happiness": -10, "smarts": 10},
             "log": "You stayed in to revise. Boring, but sensible."},
            {"text": "Ask parents for permission", "effects": {"happiness": -5},
             "log": "Your parents said no. You spent the evening sulking."},
        ],
    },
    {
        "id": "found_money",
        "min_age": 10, "max_age": 99, "prob": 0.1,
        "repeatable": True,
        "text": "You find a crumpled £20 note on the pavement.",
        "choices": [
            {"text": "Pocket it", "effects": {"money": 20, "happiness": 5},
             "log": "Finders keepers. You kept the £20."},
            {"text": "Hand it to police", "effects": {"happiness": -2, "smarts": 2},
             "log": "You handed it in. You feel self-righteous, but poorer."},
        ],
    },
    {
        "id": "career_opportunity",
        "min_age": 22, "max_age": 50, "prob": 0.2,
        "text": "A sketchy recruiter offers you a 'fast-paced' role in a new startup.",
        "choices": [
            {"text": "Take the risk", "effects": {"happiness": -15, "money": 5000, "health": -10},
             "log": "The job was terribly stressful, but it paid a quick bonus before going bust."},
            {"text": "Politely decline", "effects": {"smarts": 5, "happiness": 5},
             "log": "You avoided the startup trap. A wise choice."},
        ],
    },
    {
        "id": "family_argument",
        "min_age": 12, "max_age": 25, "prob": 0.15,
        "text": "Your parents are arguing in the kitchen. They have not noticed you yet.",
        "choices": [
            {"text": "Interrupt and defuse", "effects": {"happiness": -3, "smarts": 3},
             "log": "You stepped in. The argument stopped, but the air stayed tense."},
            {"text": "Slip away quietly", "effects": {"happiness": -5},
             "log": "You went upstairs and put your headphones on."},
            {"text": "Pick a side", "effects": {"happiness": -10},
             "log": "You took a side. One parent was relieved; the other felt betrayed."},
        ],
    },
    {
        "id": "old_friend",
        "min_age": 25, "max_age": 70, "prob": 0.12,
        "text": "An old school friend messages you out of the blue.",
        "choices": [
            {"text": "Meet for a drink", "effects": {"happiness": 8, "money": -25},
             "log": "You caught up over drinks. A good evening."},
            {"text": "Reply politely but stay distant", "effects": {"happiness": -2},
             "log": "You replied with pleasantries. Nothing came of it."},
            {"text": "Ignore the message", "effects": {"happiness": -5},
             "log": "You left them on read. It nagged at you for weeks."},
        ],
    },
]
