"""Random life events.

Each event is data. Effects, choices, age windows, probabilities — all
declared here. The event engine (core.events) reads from this list and never
encodes individual events itself.

Optional `predicates` field (Phase 6 — see core.predicates) lets an event
require specific state: a job, a stat threshold, debt, a living parent, etc.
Predicates are AND-ed; an empty/absent list means "no extra requirements".

To add a new event: append a dict here. No engine changes needed.
"""
from __future__ import annotations

from core.predicates import (
    EducationAtLeast,
    HasJob,
    HasLivingRelationship,
    HasNoLivingRelationship,
    InDebt,
    InSchool,
    JobIs,
    MaxMoney,
    MinHealth,
    MinMoney,
    MinSmarts,
    NoJob,
    DuringRecession,
    DuringWar,
    MinInflationIndex,
    RelativeHasEmployedFriend,
)

# Each "choice" maps to: text shown to player, stat/money effects, log line.
# The `log` is what gets written to the feed; the `text` is the question.

EVENTS: list[dict] = [
    # ----- Infancy / early childhood -------------------------------------
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

    # ----- Primary / secondary school ------------------------------------
    {
        "id": "primary_school_test",
        "min_age": 8, "max_age": 11, "prob": 0.4,
        "predicates": [InSchool()],
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
        "id": "school_play",
        "min_age": 7, "max_age": 13, "prob": 0.25,
        "predicates": [InSchool()],
        "text": "Your teacher offers you the lead role in the school play.",
        "choices": [
            {"text": "Take the role", "effects": {"happiness": 10, "looks": 3, "smarts": 2},
             "log": "You took the lead and got a standing ovation."},
            {"text": "Politely refuse", "effects": {"happiness": -3, "smarts": 1},
             "log": "You let someone else shine this time."},
            {"text": "Sabotage rehearsals", "effects": {"happiness": -8, "looks": -3},
             "log": "You wrecked the play. Your reputation took a knock."},
        ],
    },
    {
        "id": "best_friend",
        "min_age": 6, "max_age": 14, "prob": 0.2,
        "predicates": [HasNoLivingRelationship("Friend")],
        "text": "A kid in your class wants to be best friends.",
        "choices": [
            {"text": "Yes, of course", "effects": {"happiness": 12},
             "log": "You made a new best friend."},
            {"text": "Maybe later", "effects": {"happiness": -2},
             "log": "You hesitated. The moment passed."},
        ],
    },
    {
        "id": "teen_party",
        "min_age": 14, "max_age": 17, "prob": 0.3,
        "predicates": [InSchool()],
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
        "id": "first_crush",
        "min_age": 13, "max_age": 18, "prob": 0.2,
        "text": "You realise you have feelings for someone in your year.",
        "choices": [
            {"text": "Tell them", "effects": {"happiness": 8, "looks": 1},
             "log": "You confessed. They liked you back. Butterflies."},
            {"text": "Write a note", "effects": {"happiness": -2, "smarts": 2},
             "log": "Your handwritten note got passed around the class. Mortifying."},
            {"text": "Say nothing", "effects": {"happiness": -5},
             "log": "You said nothing. The feeling faded."},
        ],
    },
    {
        "id": "exam_results",
        "min_age": 16, "max_age": 18, "prob": 0.45,
        "predicates": [InSchool()],
        "text": "Your final school exam results have arrived in the post.",
        "choices": [
            {"text": "Open them straight away", "effects": {"smarts": 4, "happiness": 5},
             "log": "You opened them on the doorstep. Better than you feared."},
            {"text": "Wait for your parents", "effects": {"happiness": 2},
             "log": "You waited. Tears were shed; the results were respectable."},
        ],
    },

    # ----- University / early adulthood ----------------------------------
    {
        "id": "uni_freshers_week",
        "min_age": 18, "max_age": 21, "prob": 0.5,
        "predicates": [EducationAtLeast("Secondary Education")],
        "text": "It is Freshers' Week. A flatmate suggests a bar crawl.",
        "choices": [
            {"text": "All in", "effects": {"happiness": 12, "health": -8, "money": -60},
             "log": "You blacked out by 11pm. You made some friends. You also lost a shoe."},
            {"text": "One drink, then leave", "effects": {"happiness": 3, "money": -15},
             "log": "You showed your face and walked home before midnight."},
            {"text": "Stay in", "effects": {"happiness": -5, "smarts": 3},
             "log": "You stayed in and tidied your room. Boring, but useful."},
        ],
    },
    {
        "id": "dissertation",
        "min_age": 20, "max_age": 23, "prob": 0.3,
        "predicates": [EducationAtLeast("Secondary Education")],
        "text": "Your dissertation deadline is in 48 hours.",
        "choices": [
            {"text": "Pull two all-nighters", "effects": {"smarts": 6, "health": -10, "happiness": -8},
             "log": "You handed in a passable dissertation with bloodshot eyes."},
            {"text": "Pay someone to help", "effects": {"money": -400, "smarts": 1, "happiness": -2},
             "log": "You quietly paid a postgrad to 'edit' it. It got a 2:1."},
            {"text": "Submit what you have", "effects": {"smarts": -5},
             "log": "You submitted a thin draft. Your supervisor was unimpressed."},
        ],
    },
    {
        "id": "first_flat",
        "min_age": 19, "max_age": 25, "prob": 0.2,
        "predicates": [MinMoney(1_000)],
        "text": "You've found a flat to rent with a friend.",
        "choices": [
            {"text": "Sign the lease", "effects": {"happiness": 8, "money": -1_000},
             "log": "You signed the lease. Your first proper place."},
            {"text": "Back out", "effects": {"happiness": -4},
             "log": "You got cold feet and stayed with your parents."},
        ],
    },

    # ----- Career middle age ---------------------------------------------
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
        "id": "promotion_offer",
        "min_age": 25, "max_age": 55, "prob": 0.18,
        "predicates": [HasJob(), MinSmarts(60)],
        "text": "Your manager is dangling a promotion — more pay, much more responsibility.",
        "choices": [
            {"text": "Take it", "effects": {"money": 4_000, "happiness": -5, "health": -3},
             "log": "You took the promotion. The hours are brutal but the bank account is healthier."},
            {"text": "Negotiate hard", "effects": {"money": 7_000, "happiness": -2, "smarts": 2},
             "log": "You negotiated up. They were annoyed, but you got what you asked for."},
            {"text": "Refuse", "effects": {"happiness": 3},
             "log": "You said no. Your life stayed your own."},
        ],
    },
    {
        "id": "boss_wedding",
        "min_age": 25, "max_age": 55, "prob": 0.1,
        "predicates": [HasJob(), MinMoney(200)],
        "text": "You've been invited to your boss's wedding. The dress code is 'lavish'.",
        "choices": [
            {"text": "Go and dress to impress", "effects": {"money": -400, "happiness": 8, "looks": 2},
             "log": "You looked sharp. Your boss noticed."},
            {"text": "Go in your usual suit", "effects": {"happiness": 2},
             "log": "You went. Nobody really noticed you."},
            {"text": "Skip it", "effects": {"happiness": -3},
             "log": "You skipped. Awkward Monday morning."},
        ],
    },
    {
        "id": "recession_layoff_panic",
        "min_age": 22, "max_age": 65, "prob": 0.25,
        "predicates": [DuringRecession()],
        "text": "Rumours of layoffs spread as companies slash budgets during the recession.",
        "choices": [
            {"text": "Cut spending immediately", "effects": {"money": 800, "happiness": -6},
             "log": "You tightened your budget and built a small cash buffer."},
            {"text": "Ignore it and hope for the best", "effects": {"money": -600, "happiness": -8},
             "log": "You carried on spending and felt the squeeze when bills rose."},
        ],
    },
    {
        "id": "local_war_supply_shock",
        "min_age": 18, "max_age": 90, "prob": 0.22,
        "predicates": [DuringWar()],
        "text": "Regional conflict disrupts transport routes and local supplies tighten.",
        "choices": [
            {"text": "Stock up early", "effects": {"money": -450, "happiness": 2},
             "log": "You stocked up before shelves thinned out and felt prepared."},
            {"text": "Wait it out", "effects": {"money": -700, "happiness": -5},
             "log": "You waited and paid inflated prices for essentials."},
        ],
    },
    {
        "id": "inflation_rent_spike",
        "min_age": 20, "max_age": 80, "prob": 0.26,
        "predicates": [MinInflationIndex(1.18)],
        "text": "Your landlord announces a steep rent increase.",
        "choices": [
            {"text": "Negotiate and compromise", "effects": {"money": -350, "smarts": 2},
             "log": "You negotiated a smaller increase and kept the tenancy."},
            {"text": "Move to a cheaper place", "effects": {"money": -200, "happiness": -6},
             "log": "You moved to cut costs, but the upheaval wore you down."},
        ],
    },
    {
        "id": "recession_side_hustle",
        "min_age": 18, "max_age": 70, "prob": 0.2,
        "predicates": [DuringRecession(), NoJob()],
        "text": "With hiring frozen, a neighbour offers cash work for weekend help.",
        "choices": [
            {"text": "Take the side hustle", "effects": {"money": 900, "health": -4},
             "log": "You took extra shifts and kept your finances afloat."},
            {"text": "Decline and keep searching", "effects": {"happiness": -4, "smarts": 2},
             "log": "You focused on job applications and waited for a better role."},
        ],
    },
    {
        "id": "redundancy",
        "min_age": 22, "max_age": 60, "prob": 0.06,
        "predicates": [HasJob()],
        "text": "HR has asked you to a meeting. You suspect redundancies.",
        "choices": [
            {"text": "Accept the package", "effects": {"money": 3_000, "happiness": -10},
             "log": "You were made redundant. There was a payout, but the floor fell out.", "side_effect": "lose_job"},
            {"text": "Fight it", "effects": {"happiness": -5, "smarts": 3},
             "log": "You pushed back. They kept you on, but the role was diminished."},
        ],
    },
    {
        "id": "tax_audit",
        "min_age": 25, "max_age": 70, "prob": 0.05,
        "predicates": [MinMoney(5_000)],
        "text": "HMRC has opened an audit on your last three returns.",
        "choices": [
            {"text": "Hire an accountant", "effects": {"money": -800, "happiness": -3, "smarts": 2},
             "log": "Money well spent — the audit closed quietly."},
            {"text": "Do it yourself", "effects": {"money": -200, "happiness": -10, "smarts": 5},
             "log": "You read all the rules yourself. It took weeks."},
        ],
    },

    # ----- Money / lifestyle ---------------------------------------------
    {
        "id": "found_money",
        "min_age": 10, "max_age": 99, "prob": 0.1,
        "text": "You find a crumpled £20 note on the pavement.",
        "choices": [
            {"text": "Pocket it", "effects": {"money": 20, "happiness": 5},
             "log": "Finders keepers. You kept the £20."},
            {"text": "Hand it to police", "effects": {"happiness": -2, "smarts": 2},
             "log": "You handed it in. You feel self-righteous, but poorer."},
        ],
    },
    {
        "id": "scam_call",
        "min_age": 18, "max_age": 90, "prob": 0.12,
        "text": "Someone claiming to be from your bank says your account is at risk.",
        "choices": [
            {"text": "Hang up immediately", "effects": {"smarts": 2},
             "log": "You hung up. Smart move."},
            {"text": "Give them the details", "effects": {"money": -800, "happiness": -10},
             "log": "They drained your account before you realised. The bank refunded half."},
        ],
    },
    {
        "id": "lottery_win_small",
        "min_age": 18, "max_age": 99, "prob": 0.04,
        "text": "You won £200 on a scratch card.",
        "choices": [
            {"text": "Save it", "effects": {"money": 200, "smarts": 2},
             "log": "You banked the lot."},
            {"text": "Spend it on a night out", "effects": {"money": 50, "happiness": 10},
             "log": "You blew most of it in one night. Worth it."},
        ],
    },
    {
        "id": "debt_collector",
        "min_age": 22, "max_age": 90, "prob": 0.4,
        "predicates": [InDebt()],
        "text": "A debt collector is at your door.",
        "choices": [
            {"text": "Promise a payment plan", "effects": {"happiness": -5, "smarts": 1},
             "log": "You bought yourself a month."},
            {"text": "Hide and pretend you're out", "effects": {"happiness": -10, "health": -3},
             "log": "You hid behind the sofa for an hour. They left a card."},
        ],
    },

    # ----- Family / relationships ----------------------------------------
    {
        "id": "family_argument",
        "min_age": 12, "max_age": 25, "prob": 0.15,
        "predicates": [HasLivingRelationship("Mother"), HasLivingRelationship("Father")],
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
    {
        "id": "parent_health_scare",
        "min_age": 30, "max_age": 70, "prob": 0.08,
        "predicates": [HasLivingRelationship("Mother")],
        "text": "Your mother has been admitted to hospital with chest pains.",
        "choices": [
            {"text": "Drop everything and visit", "effects": {"happiness": -5, "money": -150, "health": -2},
             "log": "You sat with her all night. She made it through."},
            {"text": "Call every day", "effects": {"happiness": -8},
             "log": "You stayed home and rang every evening. She forgave you eventually."},
        ],
    },
    {
        "id": "wedding_invitation",
        "min_age": 22, "max_age": 45, "prob": 0.1,
        "predicates": [MinMoney(300)],
        "text": "A friend is getting married. The invitation includes a destination wedding in Italy.",
        "choices": [
            {"text": "Go all out", "effects": {"money": -1_500, "happiness": 15},
             "log": "You went. The wedding was beautiful and the photos are still on your wall."},
            {"text": "Send a card and a gift", "effects": {"money": -120, "happiness": -2},
             "log": "You sent a present. They understood."},
            {"text": "RSVP no", "effects": {"happiness": -5},
             "log": "You didn't go. The friendship faded."},
        ],
    },

    # ----- Mid-life --------------------------------------------------------
    {
        "id": "midlife_reset",
        "min_age": 38, "max_age": 52, "prob": 0.08,
        "text": "You stare at the ceiling at 3am and wonder if this is the life you wanted.",
        "choices": [
            {"text": "Change everything", "effects": {"happiness": 12, "money": -2_000, "health": 3},
             "log": "You quit your job, took a sabbatical, and breathed for the first time in years.",
             "side_effect": "lose_job"},
            {"text": "Take up a new hobby", "effects": {"happiness": 6, "money": -200},
             "log": "You bought a guitar. You play it sometimes."},
            {"text": "Carry on", "effects": {"happiness": -8},
             "log": "You went to work the next day as if nothing had changed."},
        ],
    },
    {
        "id": "back_injury",
        "min_age": 40, "max_age": 75, "prob": 0.1,
        "text": "You bend down to pick something up and something in your back gives way.",
        "choices": [
            {"text": "Go private", "effects": {"money": -600, "health": 8, "happiness": -2},
             "log": "An expensive specialist sorted you out within a fortnight."},
            {"text": "Wait it out on the NHS", "effects": {"health": -5, "happiness": -8},
             "log": "It took six months to see a physio. You learned to live with the ache."},
        ],
    },

    # ----- Late life -------------------------------------------------------
    {
        "id": "retirement_decision",
        "min_age": 60, "max_age": 70, "prob": 0.4,
        "predicates": [HasJob()],
        "text": "You qualify for full retirement. Your team will throw you a party.",
        "choices": [
            {"text": "Retire", "effects": {"happiness": 18, "health": 3},
             "log": "You retired. The cake was decent and the speeches were kind.",
             "side_effect": "lose_job"},
            {"text": "Stay another five years", "effects": {"money": 2_000, "health": -4, "happiness": -4},
             "log": "You worked on. The money helped, your knees did not."},
        ],
    },
    {
        "id": "garden_routine",
        "min_age": 60, "max_age": 99, "prob": 0.25,
        "text": "Your back garden has gone wild this spring.",
        "choices": [
            {"text": "Tend it yourself", "effects": {"happiness": 6, "health": 2},
             "log": "You spent the weekend pruning. The fresh air did wonders."},
            {"text": "Hire a gardener", "effects": {"money": -200, "happiness": 3},
             "log": "A local lad cut the lawn for £200. Tidy."},
            {"text": "Let it grow", "effects": {"happiness": -2},
             "log": "You let it become a meadow. The neighbours complained."},
        ],
    },
    {
        "id": "grandchild_visit",
        "min_age": 60, "max_age": 99, "prob": 0.15,
        "text": "A young relative pops in unannounced for tea.",
        "choices": [
            {"text": "Bake biscuits", "effects": {"happiness": 12, "money": -10, "health": 1},
             "log": "You baked. The biscuits were perfect."},
            {"text": "Tell a long story", "effects": {"happiness": 6, "smarts": 1},
             "log": "You told a long, rambling story. They listened."},
            {"text": "Send them away", "effects": {"happiness": -10},
             "log": "You said you were tired. They didn't visit again for months."},
        ],
    },

    # ----- Crime track (predicate-gated) ---------------------------------
    {
        "id": "gang_offer",
        "min_age": 15, "max_age": 30, "prob": 0.08,
        "predicates": [MaxMoney(200), NoJob()],
        "text": "Someone you used to go to school with offers you 'easy money' for a weekend.",
        "choices": [
            {"text": "Take the job", "effects": {"money": 800, "happiness": -2, "health": -5},
             "log": "You did it. You don't ask what it was."},
            {"text": "Refuse", "effects": {"happiness": -3, "smarts": 3},
             "log": "You refused. They lost your number."},
        ],
    },
    {
        "id": "heist_offer",
        "min_age": 22, "max_age": 50, "prob": 0.04,
        "predicates": [JobIs("fixer")],
        "text": "An associate pitches you a job lifting cash from an armoured van.",
        "choices": [
            {"text": "In", "effects": {"money": 25_000, "health": -15, "happiness": -10},
             "log": "It worked. Mostly. You'll be paying for that scar."},
            {"text": "Out", "effects": {"happiness": -2},
             "log": "You said you were out. The next week, three of them got arrested."},
        ],
    },

    # ----- Academic track (predicate-gated) ------------------------------
    {
        "id": "phd_offer",
        "min_age": 21, "max_age": 28, "prob": 0.1,
        "predicates": [EducationAtLeast("University"), MinSmarts(75)],
        "text": "A professor offers to supervise your PhD.",
        "choices": [
            {"text": "Accept", "effects": {"smarts": 10, "happiness": -8, "money": -2_000},
             "log": "You signed up for four more years of academia."},
            {"text": "Decline", "effects": {"happiness": 4},
             "log": "You walked away from the offer. Probably wisely."},
        ],
    },
    {
        "id": "tenure_track",
        "min_age": 30, "max_age": 45, "prob": 0.08,
        "predicates": [JobIs("professor")],
        "text": "Your department is opening a tenure-track position.",
        "choices": [
            {"text": "Apply", "effects": {"happiness": -5, "smarts": 6, "money": 3_000},
             "log": "You applied. You got it. The reviews took a year of your life."},
            {"text": "Stay where you are", "effects": {"happiness": 3},
             "log": "You stayed comfortable. No regrets… probably."},
        ],
    },
    {
        "id": "publish_paper",
        "min_age": 22, "max_age": 70, "prob": 0.15,
        "predicates": [MinSmarts(70), EducationAtLeast("University")],
        "text": "You have a draft paper ready to submit to a journal.",
        "choices": [
            {"text": "Submit to a top venue", "effects": {"smarts": 5, "happiness": -3},
             "log": "Months of waiting. Reject and resubmit, but you got it in eventually."},
            {"text": "Send to a smaller journal", "effects": {"smarts": 2, "happiness": 3},
             "log": "Accepted with light edits. Less prestige, less stress."},
        ],
    },

    # ----- Phase 2: NPC↔NPC graph -----
    # First event powered by the Phase 2 social graph: the player gets a
    # job referral through a *third party* — a friend of mum/dad who the
    # player doesn't know directly. The predicate reads the NPC↔NPC graph,
    # the `take_family_friend_job` side-effect mints a real career using
    # that friend's job_title. Drama from triangles, not just the star.
    {
        "id": "family_friend_referral",
        "min_age": 18, "max_age": 30, "prob": 0.10,
        "predicates": [
            NoJob(),
            HasLivingRelationship("Mother"),
            RelativeHasEmployedFriend("Mother"),
        ],
        "text": (
            "Your mother mentions an old friend of hers is looking to "
            "hire someone trustworthy at their workplace. She quietly "
            "put your name forward. Take the offer?"
        ),
        "choices": [
            {"text": "Yes — start there", "effects": {"happiness": 6},
             "log": "You took the job your mother's friend offered. "
                    "It's not glamorous, but it's a foot in the door.",
             "side_effect": "take_family_friend_job"},
            {"text": "No — you'll find your own way", "effects": {"happiness": -4},
             "log": "You thanked your mother but didn't follow up. "
                    "She tried not to look hurt."},
        ],
    },
]
