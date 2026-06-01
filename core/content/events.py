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
    OR,
    ChildCountAtMost,
    EducationAtLeast,
    HasJob,
    HasLivingRelationship,
    HasNoLivingRelationship,
    InDebt,
    InSchool,
    HasCriminalRecord,
    IsDating,
    IsIncarcerated,
    IsPregnant,
    IsSingle,
    JobIs,
    MaxMoney,
    MinChemistry,
    MinHealth,
    MinMoney,
    MinSmarts,
    NoJob,
    NOT,
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

    # ----- Phase 5: genealogy -----
    # Birth event. Available once the player has a Partner; tapers off as
    # the family grows (ChildCountAtMost(2) keeps it firing for the first
    # two would-be siblings). Accepting routes through the `have_child`
    # side-effect in core.events which mints a fresh Agent + Relationship
    # and registers the npc_id on Character.children so eligible_heirs
    # picks it up at death.
    {
        "id": "consider_child",
        # Events default to firing-once; this one needs to repeat so the
        # ChildCountAtMost(2) gate can let it offer a 2nd and 3rd child,
        # and so 'Not yet' isn't a permanent decision.
        "unique": False,
        "min_age": 22, "max_age": 42, "prob": 0.18,
        "predicates": [
            HasLivingRelationship("Partner"),
            ChildCountAtMost(2),
        ],
        "text": (
            "You and your partner have been talking about starting a family. "
            "It would change everything — and start a new line."
        ),
        "choices": [
            {"text": "Yes — start a family",
             "effects": {"happiness": 6, "money": -3_000},
             "log": "Your partner squeezed your hand. The decision was made.",
             "side_effect": "have_child"},
            {"text": "Not yet", "effects": {"happiness": -2},
             "log": "You said maybe later. Your partner nodded, quietly."},
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

    # ===========================================================
    # ----- Pregnancy v1 — probabilistic conception + gestation drama
    # `attempt_conception` rolls age/health-weighted odds; success
    # registers a pregnancy that resolves in next tick's age_up.
    # ===========================================================
    {
        "id": "broken_condom",
        "unique": False,
        "min_age": 18, "max_age": 45, "prob": 0.05,
        "predicates": [
            HasLivingRelationship("Partner"),
            ChildCountAtMost(3),
            NOT(IsPregnant()),
        ],
        "text": "Mid-evening with your partner: something didn't go as planned.",
        "choices": [
            {"text": "Get the morning-after pill", "effects": {"happiness": -2, "money": -30},
             "log": "You sorted it the next morning. £30, no fuss."},
            {"text": "Let it ride", "effects": {"happiness": 1},
             "log": "You shrugged. Whatever happens, happens.",
             "side_effect": "attempt_conception"},
        ],
    },
    {
        "id": "morning_sickness",
        "unique": False,
        "min_age": 16, "max_age": 50, "prob": 0.30,
        "predicates": [IsPregnant()],
        "text": "The mornings have been brutal. You can barely look at toast.",
        "choices": [
            {"text": "Push through the workday", "effects": {"happiness": -3, "health": -2},
             "log": "You went in. The smell of someone's coffee nearly did you in."},
            {"text": "Take a sick day", "effects": {"happiness": 2, "health": 1, "money": -50},
             "log": "You stayed home. The sofa cradled you for ten hours."},
        ],
    },
    {
        "id": "pregnant_doctor_visit",
        "unique": False,
        "min_age": 16, "max_age": 50, "prob": 0.20,
        "predicates": [IsPregnant()],
        "text": "Your antenatal appointment is today.",
        "choices": [
            {"text": "Go and ask every question", "effects": {"happiness": 3, "health": 2, "money": -40},
             "log": "The midwife was reassuring. You left with a printed list."},
            {"text": "Reschedule — work's mad", "effects": {"happiness": -3, "health": -2},
             "log": "You bumped it. You shouldn't have."},
        ],
    },
    {
        "id": "maternity_leave_question",
        "unique": False,
        "min_age": 18, "max_age": 50, "prob": 0.18,
        "predicates": [IsPregnant(), HasJob()],
        "text": "HR is asking how long you want to take off for the baby.",
        "choices": [
            {"text": "Six months", "effects": {"happiness": 4, "money": -2_000},
             "log": "Six months on a reduced rate. Worth every penny."},
            {"text": "Just the statutory minimum", "effects": {"happiness": -2, "money": -500},
             "log": "You took the minimum. The pace of work didn't soften."},
            {"text": "A full year, unpaid if needed", "effects": {"happiness": 7, "money": -8_000},
             "log": "A whole year. Painful for the bank account, priceless for you both."},
        ],
    },
    {
        "id": "nesting_instinct",
        "unique": False,
        "min_age": 16, "max_age": 50, "prob": 0.15,
        "predicates": [IsPregnant()],
        "text": "You woke up at 5am needing — urgently — to reorganise the kitchen.",
        "choices": [
            {"text": "Lean into it", "effects": {"happiness": 4, "money": -120},
             "log": "By Sunday the kitchen was unrecognisable. Joyful chaos."},
            {"text": "Go back to bed", "effects": {"happiness": 1, "health": 2},
             "log": "You slept until noon. Wisdom."},
        ],
    },

    # ===========================================================
    # ----- Love/Dating v1 — relationship-specific drama
    # Gated by IsDating / HasLivingRelationship("Partner") / IsSingle
    # so they only fire when meaningful. Repeatable (unique:False) so
    # a long arc can hit the same beat more than once.
    # ===========================================================

    # ----- Single, ages 18+ (prompts to date) -----
    {
        "id": "single_friends_set_up",
        "unique": False,
        "min_age": 18, "max_age": 45, "prob": 0.10,
        "predicates": [IsSingle(), HasLivingRelationship("Friend")],
        "text": "A friend says they know someone you'd 'really get on with'.",
        "choices": [
            {"text": "Agree to meet them", "effects": {"happiness": 3},
             "log": "You agreed to coffee with the friend-of-a-friend. It was either going to be brilliant or excruciating."},
            {"text": "Pass — you're fine alone", "effects": {"happiness": -2},
             "log": "You said you weren't looking. Your friend let it drop, kindly."},
        ],
    },
    {
        "id": "lonely_evening",
        "unique": False,
        "min_age": 20, "max_age": 70, "prob": 0.08,
        "predicates": [IsSingle()],
        "text": "It's a Friday night and the flat is quieter than you'd like.",
        "choices": [
            {"text": "Open a dating app", "effects": {"happiness": 1},
             "log": "You swiped for an hour. You weren't sure if you felt better."},
            {"text": "Call a friend instead", "effects": {"happiness": 3},
             "log": "You called someone. The silence shrank."},
            {"text": "Sit with it", "effects": {"happiness": -3},
             "log": "You sat with the loneliness. It didn't get smaller."},
        ],
    },

    # ----- Dating arc (IsDating) -----
    {
        "id": "met_their_friends",
        "unique": False,
        "min_age": 16, "max_age": 50, "prob": 0.18,
        "predicates": [IsDating()],
        "text": "They want you to meet their friends this weekend.",
        "choices": [
            {"text": "Go and charm them", "effects": {"happiness": 5, "looks": 1},
             "log": "Their friends warmed to you. You felt one step closer in."},
            {"text": "Make an excuse", "effects": {"happiness": -3},
             "log": "You bailed. They noticed. They didn't push."},
        ],
    },
    {
        "id": "dating_dinner_disaster",
        "unique": False,
        "min_age": 16, "max_age": 50, "prob": 0.12,
        "predicates": [IsDating()],
        "text": "The restaurant lost your booking and you're starving.",
        "choices": [
            {"text": "Improvise — find somewhere fun", "effects": {"happiness": 4, "smarts": 1, "money": -40},
             "log": "You found a tiny place that turned out to be perfect. Better story this way."},
            {"text": "Sulk", "effects": {"happiness": -4},
             "log": "You let the mood sour the whole evening. They were quieter than usual on the walk home."},
        ],
    },
    {
        "id": "they_met_your_parents",
        "unique": False,
        "min_age": 18, "max_age": 40, "prob": 0.12,
        "predicates": [
            IsDating(),
            OR(HasLivingRelationship("Mother"), HasLivingRelationship("Father")),
        ],
        "text": "Your parents want to meet the person you've been seeing.",
        "choices": [
            {"text": "Set up Sunday lunch", "effects": {"happiness": 5},
             "log": "Lunch was warm. Your parents liked them. Something settled in you."},
            {"text": "Stall a bit longer", "effects": {"happiness": -2},
             "log": "You told everyone it wasn't time yet. The pressure built."},
        ],
    },
    {
        "id": "dating_jealousy",
        "unique": False,
        "min_age": 17, "max_age": 50, "prob": 0.10,
        "predicates": [IsDating()],
        "text": "Someone keeps liking all their photos online. You don't recognise them.",
        "choices": [
            {"text": "Ask about it calmly", "effects": {"happiness": -1, "smarts": 1},
             "log": "You asked. It was a friend from school. You felt slightly silly, mostly relieved."},
            {"text": "Stew over it", "effects": {"happiness": -5},
             "log": "You said nothing for a week. The thought ate at you."},
            {"text": "Confront them", "effects": {"happiness": -4},
             "log": "You came in hot. The argument took two days to smooth over."},
        ],
    },
    {
        "id": "dating_move_in_question",
        "unique": False,
        "min_age": 19, "max_age": 45, "prob": 0.08,
        "predicates": [IsDating(), MinChemistry(50)],
        "text": "They're hinting at moving in together.",
        "choices": [
            {"text": "Say yes", "effects": {"happiness": 6, "money": -200},
             "log": "You said yes. Boxes everywhere for a week. You both meant it."},
            {"text": "Ask for more time", "effects": {"happiness": -2},
             "log": "You said you weren't ready. They nodded, but the air shifted."},
            {"text": "Say no", "effects": {"happiness": -5},
             "log": "You said no, clearly. Something between you cooled."},
        ],
    },

    # ----- Partnered (HasLivingRelationship("Partner")) -----
    {
        "id": "partner_late_night",
        "unique": False,
        "min_age": 20, "max_age": 70, "prob": 0.10,
        "predicates": [HasLivingRelationship("Partner")],
        "text": "Your partner came in at 2am and didn't text.",
        "choices": [
            {"text": "Ask what happened", "effects": {"happiness": -1, "smarts": 1},
             "log": "You asked. They explained. It was nothing, this time."},
            {"text": "Pretend not to notice", "effects": {"happiness": -4},
             "log": "You said nothing. It festered."},
            {"text": "Lose your temper", "effects": {"happiness": -6},
             "log": "You shouted. The morning was very quiet."},
        ],
    },
    {
        "id": "partner_career_offer",
        "unique": False,
        "min_age": 22, "max_age": 55, "prob": 0.07,
        "predicates": [HasLivingRelationship("Partner")],
        "text": "Your partner has been offered a great job — in another city.",
        "choices": [
            {"text": "Support the move", "effects": {"happiness": 4, "money": -2_000},
             "log": "You moved together. The first months were hard; you don't regret it."},
            {"text": "Ask them to stay", "effects": {"happiness": -3},
             "log": "They turned the job down. You both pretended it wasn't an issue."},
            {"text": "Try long-distance", "effects": {"happiness": -5},
             "log": "Weekends only. The phone bill went up. So did the silences."},
        ],
    },
    {
        "id": "partner_surprise_gift",
        "unique": False,
        "min_age": 19, "max_age": 90, "prob": 0.08,
        "predicates": [HasLivingRelationship("Partner")],
        "text": "Your partner surprised you with something thoughtful.",
        "choices": [
            {"text": "Be moved by it", "effects": {"happiness": 7},
             "log": "You actually teared up. They were chuffed."},
        ],
    },
    {
        "id": "partner_wants_a_pet",
        "unique": False,
        "min_age": 20, "max_age": 60, "prob": 0.07,
        "predicates": [HasLivingRelationship("Partner")],
        "text": "Your partner wants the two of you to get a pet.",
        "choices": [
            {"text": "Yes — a dog", "effects": {"happiness": 6, "money": -400},
             "log": "You picked up the puppy together. Mess, joy, mud."},
            {"text": "Yes — a cat", "effects": {"happiness": 5, "money": -200},
             "log": "A cat moved in. Took two weeks to come out from under the sofa."},
            {"text": "Not yet", "effects": {"happiness": -3},
             "log": "You said maybe later. They tried not to look disappointed."},
        ],
    },
    {
        "id": "partner_health_scare",
        "unique": False,
        "min_age": 30, "max_age": 80, "prob": 0.06,
        "predicates": [HasLivingRelationship("Partner")],
        "text": "Your partner's check-up came back with something to investigate.",
        "choices": [
            {"text": "Drop everything to be there", "effects": {"happiness": -2, "health": -1},
             "log": "You held their hand through every scan. Results came back fine. You both cried."},
            {"text": "Carry on as normal to keep things steady", "effects": {"happiness": -4},
             "log": "You tried to act like nothing was wrong. They needed more than that."},
        ],
    },
    {
        "id": "partner_lost_their_job",
        "unique": False,
        "min_age": 22, "max_age": 65, "prob": 0.07,
        "predicates": [HasLivingRelationship("Partner")],
        "text": "Your partner came home and said they'd been let go.",
        "choices": [
            {"text": "Cover the bills for now", "effects": {"happiness": 2, "money": -1_000},
             "log": "You took the pressure off them for a few months. They got back on their feet."},
            {"text": "Push them to job-hunt hard", "effects": {"happiness": -3},
             "log": "You meant well. They heard pressure where you'd meant support."},
        ],
    },
    {
        "id": "partner_anniversary_milestone",
        "unique": False,
        "min_age": 25, "max_age": 90, "prob": 0.05,
        "predicates": [HasLivingRelationship("Partner")],
        "text": "It's a big anniversary year — a decade together.",
        "choices": [
            {"text": "Plan something big", "effects": {"happiness": 10, "money": -800},
             "log": "Long weekend away. You laughed about the early days. Worth £800."},
            {"text": "Renew vows / make a private commitment", "effects": {"happiness": 8},
             "log": "Just the two of you, no fuss. Said the things out loud."},
            {"text": "Let it pass quietly", "effects": {"happiness": -4},
             "log": "Neither of you mentioned it. It hung in the air for weeks."},
        ],
    },
    {
        "id": "partner_argument",
        "unique": False,
        "min_age": 20, "max_age": 90, "prob": 0.12,
        "predicates": [HasLivingRelationship("Partner")],
        "text": "A small thing has turned into a serious argument.",
        "choices": [
            {"text": "Apologise first", "effects": {"happiness": 1, "smarts": 1},
             "log": "You broke the standoff. It cost something. It was the right call."},
            {"text": "Stand your ground", "effects": {"happiness": -4},
             "log": "Neither of you backed down. The flat felt smaller for a week."},
            {"text": "Walk away to cool off", "effects": {"happiness": -1},
             "log": "You took a long walk. By the time you got back, both of you had softened."},
        ],
    },
    {
        "id": "partner_brings_up_marriage",
        "unique": False,
        "min_age": 23, "max_age": 50, "prob": 0.06,
        "predicates": [HasLivingRelationship("Partner")],
        "text": "Your partner has started talking about marriage.",
        "choices": [
            {"text": "Yes — let's plan it", "effects": {"happiness": 9},
             "log": "You said yes. Pints, tears, phone calls. Everyone you love knew by Tuesday."},
            {"text": "Not yet — but one day", "effects": {"happiness": -2},
             "log": "You said you weren't ready. They were patient, but quieter for a while."},
            {"text": "It's not for you", "effects": {"happiness": -5},
             "log": "You said it wouldn't be happening. Something between you cracked."},
        ],
    },

    # ----- Single (after a Partner ended) -----
    {
        "id": "post_breakup_low",
        "unique": False,
        "min_age": 18, "max_age": 80, "prob": 0.10,
        "predicates": [IsSingle()],
        "text": "A song came on the radio and the past hit you sideways.",
        "choices": [
            {"text": "Let yourself feel it", "effects": {"happiness": -2, "smarts": 1},
             "log": "You sat with the feeling. It moved through you, eventually."},
            {"text": "Distract yourself hard", "effects": {"happiness": -1},
             "log": "You filled the evening with errands. It mostly worked."},
        ],
    },

    # ===========================================================
    # ----- Phase 6: content batch (40 events across life phases)
    # Predicates reuse existing infrastructure; no new gating types.
    # Grouped by life phase in declaration order for readability.
    # ===========================================================

    # ----- Childhood (ages 5–11) -----
    {
        "id": "school_field_trip",
        "min_age": 6, "max_age": 11, "prob": 0.18,
        "text": "Your class is going on a field trip to a museum.",
        "choices": [
            {"text": "Pay attention", "effects": {"smarts": 3, "happiness": 2},
             "log": "You stared at the dinosaur bones for an hour. Something clicked."},
            {"text": "Mess about with friends", "effects": {"happiness": 4, "smarts": -1},
             "log": "You barely saw the exhibits, but you laughed until you cried."},
        ],
    },
    {
        "id": "bully_incident",
        "min_age": 6, "max_age": 11, "prob": 0.14,
        "text": "An older kid keeps picking on you in the playground.",
        "choices": [
            {"text": "Tell a teacher", "effects": {"happiness": 2},
             "log": "You spoke to a teacher. The bullying stopped, mostly."},
            {"text": "Stand up to them", "effects": {"happiness": 3, "health": -2},
             "log": "You squared up. You got pushed once, but they left you alone after."},
            {"text": "Avoid them", "effects": {"happiness": -3},
             "log": "You took long ways to class. It worked, but it weighed on you."},
        ],
    },
    {
        "id": "lost_a_tooth",
        "min_age": 5, "max_age": 9, "prob": 0.20,
        "text": "Your tooth came out at the dinner table.",
        "choices": [
            {"text": "Put it under the pillow", "effects": {"happiness": 3, "money": 2},
             "log": "The Tooth Fairy left you £2 and a feeling of being known."},
        ],
    },
    {
        "id": "school_play",
        "min_age": 7, "max_age": 11, "prob": 0.12,
        "text": "Auditions for the school play are open.",
        "choices": [
            {"text": "Try for the lead role", "effects": {"happiness": 5, "looks": 1},
             "log": "You got a part. People clapped. You'll remember it."},
            {"text": "Help with the set", "effects": {"happiness": 2, "smarts": 1},
             "log": "You painted backdrops. Quietly satisfying work."},
            {"text": "Skip it", "effects": {"happiness": -1},
             "log": "You didn't try out. You wondered, later, if you should have."},
        ],
    },
    {
        "id": "got_a_pet",
        "min_age": 5, "max_age": 11, "prob": 0.10,
        "text": "Your parents say you can have a pet.",
        "choices": [
            {"text": "A dog", "effects": {"happiness": 6, "health": 1},
             "log": "You named the dog something embarrassing. You loved it."},
            {"text": "A cat", "effects": {"happiness": 5},
             "log": "The cat tolerated you. You took what affection it gave."},
            {"text": "A fish", "effects": {"happiness": 2},
             "log": "The fish lived a quiet, glassy life."},
        ],
    },
    {
        "id": "skinned_knee",
        "min_age": 5, "max_age": 10, "prob": 0.15,
        "text": "You fell off your bike on the way home.",
        "choices": [
            {"text": "Get up and ride on", "effects": {"happiness": -1, "health": -1},
             "log": "Your knee bled through your jeans. You kept going."},
        ],
    },
    {
        "id": "sleepover_invite",
        "min_age": 7, "max_age": 11, "prob": 0.16,
        "text": "A classmate invited you to a sleepover.",
        "choices": [
            {"text": "Go", "effects": {"happiness": 5},
             "log": "You ate too much pizza and laughed until 2am."},
            {"text": "Stay home", "effects": {"happiness": -2},
             "log": "You stayed in. You heard about it for weeks at school."},
        ],
    },
    {
        "id": "science_fair",
        "min_age": 8, "max_age": 11, "prob": 0.13,
        "text": "The science fair is next month.",
        "choices": [
            {"text": "Build a project", "effects": {"smarts": 4, "happiness": 2},
             "log": "Your volcano didn't erupt right, but you learned things."},
            {"text": "Pass on it", "effects": {"happiness": -1},
             "log": "You sat in the audience. The winning project was a robot arm."},
        ],
    },

    # ----- Teen (12–17) -----
    {
        "id": "first_crush",
        "min_age": 12, "max_age": 17, "prob": 0.18,
        "text": "There's someone at school you can't stop thinking about.",
        "choices": [
            {"text": "Tell them", "effects": {"happiness": 4, "looks": 1},
             "log": "You said it. It was awkward and electric and worth it."},
            {"text": "Hold it in", "effects": {"happiness": -3},
             "log": "You said nothing. The feeling stayed for months."},
        ],
    },
    {
        "id": "caught_skipping_class",
        "min_age": 13, "max_age": 17, "prob": 0.12,
        "predicates": [InSchool()],
        "text": "You skipped period three. The vice-principal saw you.",
        "choices": [
            {"text": "Apologise", "effects": {"happiness": -1, "smarts": 1},
             "log": "You took the detention quietly. It blew over in a week."},
            {"text": "Argue", "effects": {"happiness": -3, "smarts": -1},
             "log": "It went badly. You ended up suspended for two days."},
        ],
    },
    {
        "id": "school_award",
        "min_age": 12, "max_age": 17, "prob": 0.10,
        "predicates": [InSchool(), MinSmarts(60)],
        "text": "You're up for an academic award at end-of-year assembly.",
        "choices": [
            {"text": "Show up and collect it", "effects": {"smarts": 3, "happiness": 5},
             "log": "Your name came over the speakers. You felt taller for a day."},
        ],
    },
    {
        "id": "cyberbullying",
        "min_age": 12, "max_age": 17, "prob": 0.10,
        "text": "Someone's posting cruel things about you online.",
        "choices": [
            {"text": "Tell an adult", "effects": {"happiness": -2},
             "log": "Your parents took it seriously. It mostly stopped."},
            {"text": "Block and move on", "effects": {"happiness": -4},
             "log": "You stopped checking. The bad feeling lingered."},
            {"text": "Fight back online", "effects": {"happiness": -6, "looks": -1},
             "log": "You said worse things back. It spiralled. You regretted it."},
        ],
    },
    {
        "id": "drivers_test",
        "min_age": 16, "max_age": 17, "prob": 0.30,
        "text": "Your driving test is next week.",
        "choices": [
            {"text": "Practice hard", "effects": {"smarts": 2, "happiness": 4},
             "log": "You passed. The car feels like a key to the world."},
            {"text": "Wing it", "effects": {"happiness": -3, "money": -80},
             "log": "You failed. You'll have to pay to retake it."},
        ],
    },
    {
        "id": "underage_drinking",
        "min_age": 14, "max_age": 17, "prob": 0.12,
        "text": "An older friend offered you a beer at a party.",
        "choices": [
            {"text": "Try it", "effects": {"happiness": 4, "health": -2},
             "log": "You tried it. It was bitter. You felt grown."},
            {"text": "Pass", "effects": {"happiness": 1, "health": 1},
             "log": "You said no. It wasn't a big deal."},
        ],
    },
    {
        "id": "first_concert",
        "min_age": 14, "max_age": 17, "prob": 0.14,
        "predicates": [MinMoney(50)],
        "text": "Your favourite band is playing in town.",
        "choices": [
            {"text": "Go", "effects": {"happiness": 8, "money": -60},
             "log": "You screamed every lyric. Your ears rang for a day."},
            {"text": "Save the money", "effects": {"happiness": -2, "money": 0},
             "log": "You watched the highlights online. It wasn't the same."},
        ],
    },
    {
        "id": "argument_with_parent",
        "min_age": 12, "max_age": 19, "prob": 0.14,
        "predicates": [OR(HasLivingRelationship("Mother"), HasLivingRelationship("Father"))],
        "text": "You and a parent are shouting at each other again.",
        "choices": [
            {"text": "Apologise first", "effects": {"happiness": -1, "smarts": 1},
             "log": "You said sorry. It cost something. It was the right call."},
            {"text": "Storm out", "effects": {"happiness": -4},
             "log": "You slammed the door. Dinner was tense for a week."},
        ],
    },

    # ----- Young adult / university (18–24) -----
    {
        "id": "party_at_uni",
        "min_age": 18, "max_age": 24, "prob": 0.18,
        "text": "There's a party at someone's flat tonight.",
        "choices": [
            {"text": "Go", "effects": {"happiness": 6, "smarts": -1, "health": -1},
             "log": "It was loud, sweaty, brilliant. You found your tribe."},
            {"text": "Stay in and study", "effects": {"smarts": 3, "happiness": -2},
             "log": "You stayed in. You got real work done."},
        ],
    },
    {
        "id": "all_nighter",
        "min_age": 18, "max_age": 24, "prob": 0.15,
        "predicates": [InSchool()],
        "text": "A deadline is tomorrow and you've barely started.",
        "choices": [
            {"text": "Pull an all-nighter", "effects": {"smarts": 3, "health": -3, "happiness": -2},
             "log": "You finished at 6am. The submission scraped through."},
            {"text": "Hand it in late", "effects": {"smarts": -2, "happiness": -1},
             "log": "You took the late penalty. You slept properly, at least."},
        ],
    },
    {
        "id": "spring_break",
        "min_age": 18, "max_age": 24, "prob": 0.08,
        "predicates": [MinMoney(400)],
        "text": "Friends are organising a spring-break trip.",
        "choices": [
            {"text": "Join them", "effects": {"happiness": 10, "money": -500},
             "log": "The trip cost more than you planned. You'd do it again."},
            {"text": "Skip it", "effects": {"happiness": -3},
             "log": "You watched their photos roll in. Bittersweet."},
        ],
    },
    {
        "id": "study_group",
        "min_age": 18, "max_age": 24, "prob": 0.16,
        "predicates": [InSchool()],
        "text": "A classmate is starting a study group for finals.",
        "choices": [
            {"text": "Join", "effects": {"smarts": 3, "happiness": 2},
             "log": "You learned things faster, and made a real friend."},
            {"text": "Pass", "effects": {"smarts": 1},
             "log": "You preferred to study alone. It worked, slowly."},
        ],
    },
    {
        "id": "lost_textbook",
        "min_age": 18, "max_age": 24, "prob": 0.10,
        "predicates": [InSchool()],
        "text": "You can't find your textbook anywhere and the lecturer is strict.",
        "choices": [
            {"text": "Buy a replacement", "effects": {"money": -80, "smarts": 1},
             "log": "You forked out for a new copy. Painful."},
            {"text": "Borrow from a friend", "effects": {"happiness": 1},
             "log": "You got through term sharing. Not ideal, but free."},
        ],
    },
    {
        "id": "internship_offer",
        "min_age": 19, "max_age": 24, "prob": 0.10,
        "predicates": [NoJob(), MinSmarts(55)],
        "text": "A summer internship offer just landed in your inbox.",
        "choices": [
            {"text": "Take it", "effects": {"smarts": 3, "happiness": 3, "money": 1_500},
             "log": "You spent the summer in a real office. Money, contacts, a glimpse."},
            {"text": "Decline", "effects": {"happiness": 1},
             "log": "You took the summer off. You needed it."},
        ],
    },

    # ----- Work (HasJob) -----
    {
        "id": "annoying_coworker",
        "min_age": 18, "max_age": 65, "prob": 0.12,
        "predicates": [HasJob()],
        "text": "A coworker keeps interrupting you all day.",
        "choices": [
            {"text": "Talk to them directly", "effects": {"happiness": 2, "smarts": 1},
             "log": "You had the conversation. It mostly worked."},
            {"text": "Suffer in silence", "effects": {"happiness": -4},
             "log": "You said nothing. It ate at you for weeks."},
        ],
    },
    {
        "id": "office_party",
        "min_age": 18, "max_age": 65, "prob": 0.10,
        "predicates": [HasJob()],
        "text": "The office Christmas party is tonight.",
        "choices": [
            {"text": "Go and enjoy it", "effects": {"happiness": 4},
             "log": "It was awkward and warm and you stayed too late."},
            {"text": "Make a brief appearance", "effects": {"happiness": 1},
             "log": "Forty minutes, two drinks, gone. Just right."},
            {"text": "Skip it", "effects": {"happiness": -2},
             "log": "You skipped. Monday felt slightly colder."},
        ],
    },
    {
        "id": "difficult_client",
        "min_age": 18, "max_age": 65, "prob": 0.13,
        "predicates": [HasJob()],
        "text": "A client is demanding the impossible by Friday.",
        "choices": [
            {"text": "Push back", "effects": {"happiness": -1, "smarts": 2, "money": 200},
             "log": "You negotiated the scope. They paid the rush fee."},
            {"text": "Grind it out", "effects": {"happiness": -5, "health": -2, "money": 400},
             "log": "You delivered by Friday. You owe yourself a weekend."},
        ],
    },
    {
        "id": "conference_trip",
        "min_age": 22, "max_age": 65, "prob": 0.08,
        "predicates": [HasJob(), MinSmarts(55)],
        "text": "Your employer wants you to attend an industry conference.",
        "choices": [
            {"text": "Go", "effects": {"smarts": 4, "happiness": 3},
             "log": "You came back with three new ideas and one new contact."},
            {"text": "Pass", "effects": {"happiness": -1},
             "log": "You stayed home. Caught up on email instead."},
        ],
    },
    {
        "id": "coffee_spill",
        "min_age": 18, "max_age": 65, "prob": 0.06,
        "predicates": [HasJob()],
        "text": "You knocked a full coffee onto your laptop.",
        "choices": [
            {"text": "Pay for a repair", "effects": {"money": -250, "happiness": -3},
             "log": "Two hundred and fifty quid and three lost hours."},
        ],
    },
    {
        "id": "mentor_at_work",
        "min_age": 19, "max_age": 45, "prob": 0.08,
        "predicates": [HasJob()],
        "text": "A senior at work has offered to mentor you.",
        "choices": [
            {"text": "Accept gratefully", "effects": {"smarts": 4, "happiness": 3},
             "log": "They opened a door you didn't know existed."},
            {"text": "Politely decline", "effects": {"happiness": -1},
             "log": "You said you'd think about it. You never followed up."},
        ],
    },
    {
        "id": "side_project_idea",
        "min_age": 20, "max_age": 50, "prob": 0.10,
        "predicates": [HasJob(), MinSmarts(60)],
        "text": "You have an idea you can't stop thinking about.",
        "choices": [
            {"text": "Build it in the evenings", "effects": {"smarts": 3, "happiness": -3, "health": -1},
             "log": "You worked weekends for months. The thing exists now."},
            {"text": "Let it go", "effects": {"happiness": -2},
             "log": "You wrote it down and moved on. It still nags."},
        ],
    },
    {
        "id": "coworker_wedding_invite",
        "min_age": 22, "max_age": 60, "prob": 0.07,
        "predicates": [HasJob()],
        "text": "A coworker invited you to their wedding.",
        "choices": [
            {"text": "Go and bring a gift", "effects": {"happiness": 3, "money": -120},
             "log": "Open bar, slow speeches, real joy. £120 well spent."},
            {"text": "Send a card", "effects": {"happiness": 1, "money": -10},
             "log": "You sent a thoughtful card. They appreciated it."},
        ],
    },

    # ----- Money & misc -----
    {
        "id": "found_money_on_street",
        "min_age": 6, "max_age": 90, "prob": 0.06,
        "text": "You spotted a twenty on the pavement.",
        "choices": [
            {"text": "Pocket it", "effects": {"money": 20, "happiness": 2},
             "log": "Twenty quid the universe owed you. You took it."},
            {"text": "Hand it to a stranger", "effects": {"happiness": 3},
             "log": "An older man thanked you, surprised. You felt lighter."},
        ],
    },
    {
        "id": "small_lottery_win",
        "min_age": 18, "max_age": 90, "prob": 0.03,
        "text": "You checked your numbers. You matched a few.",
        "choices": [
            {"text": "Cash it", "effects": {"money": 500, "happiness": 6},
             "log": "Five hundred quid. Not life-changing, but it bought a week of ease."},
        ],
    },
    {
        "id": "online_scam_email",
        "min_age": 14, "max_age": 90, "prob": 0.08,
        "text": "An urgent email says your bank account is at risk. Click here.",
        "choices": [
            {"text": "Click the link", "effects": {"money": -300, "happiness": -5},
             "log": "It was a scam. They took £300 before you froze the card."},
            {"text": "Delete it", "effects": {"smarts": 1},
             "log": "You knew what it was. You deleted it and moved on."},
        ],
    },
    {
        "id": "subscription_creep",
        "min_age": 18, "max_age": 90, "prob": 0.10,
        "text": "Your monthly subscriptions are silently larger than they were last year.",
        "choices": [
            {"text": "Audit and cancel a few", "effects": {"money": 60, "smarts": 1},
             "log": "Forty minutes of admin saved you £60 a month."},
            {"text": "Ignore it", "effects": {"money": -40, "happiness": -1},
             "log": "It went up by another tenner. You didn't notice for months."},
        ],
    },
    {
        "id": "broken_phone",
        "min_age": 12, "max_age": 90, "prob": 0.07,
        "text": "Your phone screen shattered against the pavement.",
        "choices": [
            {"text": "Repair it", "effects": {"money": -120, "happiness": -2},
             "log": "Repair shop fixed it in an hour. £120."},
            {"text": "Live with the cracks", "effects": {"happiness": -3, "money": 0},
             "log": "Glass shards in your thumb for weeks. You'll deal with it later."},
        ],
    },

    # ----- Relationship-flavoured -----
    {
        "id": "family_reunion",
        "min_age": 8, "max_age": 80, "prob": 0.07,
        "predicates": [OR(HasLivingRelationship("Mother"), HasLivingRelationship("Father"),
                          HasLivingRelationship("Sibling"))],
        "text": "There's a family reunion coming up.",
        "choices": [
            {"text": "Go", "effects": {"happiness": 4},
             "log": "You hugged people you hadn't seen in years. Worth the trip."},
            {"text": "Stay home", "effects": {"happiness": -3},
             "log": "You stayed in. Your absence was noted."},
        ],
    },
    {
        "id": "friend_in_trouble",
        "min_age": 14, "max_age": 70, "prob": 0.10,
        "predicates": [HasLivingRelationship("Friend"), MinMoney(200)],
        "text": "A close friend asks if they can borrow £200 — they sound desperate.",
        "choices": [
            {"text": "Lend it", "effects": {"money": -200, "happiness": 3},
             "log": "You handed over the cash. They cried, a little."},
            {"text": "Say you can't", "effects": {"happiness": -4},
             "log": "You said no. They understood. Something shifted between you anyway."},
        ],
    },
    {
        "id": "sibling_needs_favor",
        "min_age": 14, "max_age": 70, "prob": 0.10,
        "predicates": [HasLivingRelationship("Sibling")],
        "text": "Your sibling needs you to help them move this weekend.",
        "choices": [
            {"text": "Show up with a van", "effects": {"happiness": 3, "health": -1},
             "log": "Eight hours of stairs and pizza. They'll owe you."},
            {"text": "Say you're busy", "effects": {"happiness": -3},
             "log": "You begged off. They went quiet for a while."},
        ],
    },
    {
        "id": "partner_anniversary",
        "min_age": 20, "max_age": 90, "prob": 0.10,
        "predicates": [HasLivingRelationship("Partner")],
        "text": "Today's your anniversary with your partner.",
        "choices": [
            {"text": "Plan something special", "effects": {"happiness": 6, "money": -150},
             "log": "Candles, a real dinner, a long walk. You both meant it."},
            {"text": "Cook at home", "effects": {"happiness": 3, "money": -25},
             "log": "Pasta and a bottle of wine. Quiet, perfect."},
            {"text": "Forget it", "effects": {"happiness": -6},
             "log": "You remembered at midnight. It was a long apology."},
        ],
    },
    {
        "id": "yearly_checkup",
        "min_age": 18, "max_age": 90, "prob": 0.08,
        "text": "It's been a while since you saw a doctor for a routine check.",
        "choices": [
            {"text": "Go", "effects": {"health": 3, "money": -50},
             "log": "Bloods fine. £50 well spent on knowing."},
            {"text": "Skip it", "effects": {"health": -1, "happiness": -1},
             "log": "You meant to book. You didn't."},
        ],
    },

    # ===========================================================
    # ----- Crime v1 — prison drama + post-release record drag
    # IsIncarcerated events are the only ones eligible to fire while
    # the player is inside (see core/events.roll_event). The two
    # HasCriminalRecord events kick in after release.
    # ===========================================================
    {
        "id": "prison_yard_fight",
        "unique": False,
        "min_age": 12, "max_age": 90, "prob": 0.20,
        "predicates": [IsIncarcerated()],
        "text": "Someone in the yard squared up to you over nothing.",
        "choices": [
            {"text": "Throw the first punch", "effects": {"health": -8, "happiness": 2},
             "log": "You swung first. You held your own. Word got around."},
            {"text": "Back down", "effects": {"happiness": -4},
             "log": "You walked away. The yard noticed. Some respected it; some didn't."},
        ],
    },
    {
        "id": "prison_education_program",
        "unique": False,
        "min_age": 16, "max_age": 90, "prob": 0.18,
        "predicates": [IsIncarcerated()],
        "text": "A sign-up sheet is going round for the prison education program.",
        "choices": [
            {"text": "Sign up", "effects": {"smarts": 4, "happiness": 3},
             "log": "Two evenings a week with a real tutor. You felt like a person again."},
            {"text": "Pass", "effects": {"happiness": -1},
             "log": "You passed. Same routine, same noise."},
        ],
    },
    {
        "id": "prison_parole_hearing",
        "unique": False,
        "min_age": 16, "max_age": 90, "prob": 0.10,
        "predicates": [IsIncarcerated()],
        "text": "You've got a parole hearing this week.",
        "choices": [
            {"text": "Express genuine remorse", "effects": {"happiness": 4},
             "log": "You meant what you said. The board wasn't moved enough to release you, but it helped."},
            {"text": "Refuse to play along", "effects": {"happiness": -3},
             "log": "You stayed silent through the questions. The hearing was over in ten minutes."},
        ],
    },
    {
        "id": "ex_con_job_rejection",
        "unique": False,
        "min_age": 18, "max_age": 65, "prob": 0.10,
        "predicates": [HasCriminalRecord(), NoJob()],
        "text": "The interview went well until they ran the background check.",
        "choices": [
            {"text": "Keep applying anyway", "effects": {"happiness": -3, "smarts": 1},
             "log": "You sent ten more applications that week. Two replied. Neither was great."},
            {"text": "Go where they don't ask", "effects": {"happiness": -1, "money": 200},
             "log": "Cash-in-hand work, mostly. £200 this fortnight."},
        ],
    },
    {
        "id": "parole_officer_check_in",
        "unique": False,
        "min_age": 16, "max_age": 80, "prob": 0.12,
        "predicates": [HasCriminalRecord()],
        "text": "Your parole officer wants to see you Thursday.",
        "choices": [
            {"text": "Show up sober and on time", "effects": {"happiness": 2, "smarts": 1},
             "log": "You arrived early. The officer noted it. Small steps."},
            {"text": "Miss the appointment", "effects": {"happiness": -5},
             "log": "You forgot. They left two messages and a warning."},
        ],
    },
]
