"""Final school exam — content, generation and grading.

Sat at 18 when secondary school ends. The exam is a short multiple-choice
quiz: the first question is always the player's name (a free, easy point),
followed by nine general-knowledge questions drawn from at least three of the
subject groups, ordered easy to hard.

Questions are deliberately *general* (no country-specific trivia) so the quiz
plays fairly wherever the player is from. The final grade (F–A) is blended
with the player's smarts and decides university admission and scholarships.
"""
from __future__ import annotations

from core.rng import Rng

SUBJECTS = ["English", "Math and Science", "History and Religious Studies", "Geography"]

# Each question: prompt, three options, index of the correct option, difficulty 1-3.
QUESTIONS: dict[str, list[dict]] = {
    "English": [
        {"prompt": "Which word means the same as 'happy'?", "options": ["Joyful", "Hungry", "Tall"], "answer": 0, "difficulty": 1},
        {"prompt": "What is the plural of 'child'?", "options": ["Childs", "Children", "Childes"], "answer": 1, "difficulty": 1},
        {"prompt": "Which word is the opposite of 'fast'?", "options": ["Quick", "Slow", "Bright"], "answer": 1, "difficulty": 2},
        {"prompt": "Which sentence is written correctly?", "options": ["She go to school.", "She goes to school.", "She going school."], "answer": 1, "difficulty": 2},
        {"prompt": "Which word is spelled correctly?", "options": ["Recieve", "Receive", "Receeve"], "answer": 1, "difficulty": 3},
        {"prompt": "A word that describes a noun is called a(n)…", "options": ["Adjective", "Volcano", "Triangle"], "answer": 0, "difficulty": 3},
    ],
    "Math and Science": [
        {"prompt": "What is 7 + 5?", "options": ["11", "12", "13"], "answer": 1, "difficulty": 1},
        {"prompt": "How many sides does a triangle have?", "options": ["3", "4", "5"], "answer": 0, "difficulty": 1},
        {"prompt": "What is 6 × 7?", "options": ["42", "36", "48"], "answer": 0, "difficulty": 2},
        {"prompt": "Which gas do humans need to breathe to survive?", "options": ["Oxygen", "Helium", "Hydrogen"], "answer": 0, "difficulty": 2},
        {"prompt": "What is the chemical symbol for water?", "options": ["CO2", "H2O", "O2"], "answer": 1, "difficulty": 3},
        {"prompt": "What is 144 ÷ 12?", "options": ["12", "14", "11"], "answer": 0, "difficulty": 3},
    ],
    "History and Religious Studies": [
        {"prompt": "How many days are there in a week?", "options": ["5", "6", "7"], "answer": 2, "difficulty": 1},
        {"prompt": "Which of these is a major world religion?", "options": ["Photosynthesis", "Buddhism", "Calculus"], "answer": 1, "difficulty": 1},
        {"prompt": "Ancient pyramids are most associated with which country?", "options": ["Egypt", "Canada", "Norway"], "answer": 0, "difficulty": 2},
        {"prompt": "Which book is the holy text of Islam?", "options": ["The Quran", "The Odyssey", "The Atlas"], "answer": 0, "difficulty": 2},
        {"prompt": "About how many years are in a century?", "options": ["10", "100", "1000"], "answer": 1, "difficulty": 3},
        {"prompt": "A period before written records is called…", "options": ["Prehistory", "Geography", "Arithmetic"], "answer": 0, "difficulty": 3},
    ],
    "Geography": [
        {"prompt": "How many continents are there on Earth?", "options": ["5", "7", "9"], "answer": 1, "difficulty": 1},
        {"prompt": "Which is the largest ocean?", "options": ["Atlantic", "Pacific", "Indian"], "answer": 1, "difficulty": 1},
        {"prompt": "Which of these is a desert?", "options": ["Sahara", "Amazon", "Everest"], "answer": 0, "difficulty": 2},
        {"prompt": "What do we call frozen water that falls from the sky?", "options": ["Snow", "Sand", "Smoke"], "answer": 0, "difficulty": 2},
        {"prompt": "What is the name for a piece of land surrounded by water?", "options": ["Island", "Mountain", "Valley"], "answer": 0, "difficulty": 3},
        {"prompt": "The imaginary line around the middle of the Earth is the…", "options": ["Equator", "Horizon", "Meridian of nothing"], "answer": 0, "difficulty": 3},
    ],
}

_NAME_DISTRACTORS = ["Sam", "Alex", "Jordan", "Riley", "Casey", "Taylor", "Morgan", "Jamie"]

GRADE_ORDER = ["F", "E", "D", "C", "B", "A"]


def _shuffle(rng: Rng, items: list) -> list:
    out = list(items)
    for i in range(len(out) - 1, 0, -1):
        j = rng.randint(0, i)
        out[i], out[j] = out[j], out[i]
    return out


def _name_question(rng: Rng, first_name: str) -> dict:
    name = (first_name or "You").strip() or "You"
    distractors = [d for d in _NAME_DISTRACTORS if d.lower() != name.lower()]
    picks = _shuffle(rng, distractors)[:2]
    options = _shuffle(rng, [name] + picks)
    return {
        "prompt": "What is your name?",
        "options": options,
        "answer": options.index(name),
        "difficulty": 0,
        "subject": "Warm-up",
    }


def generate_exam(rng: Rng, first_name: str) -> dict:
    """Build a fresh 10-question exam. Deterministic for a given rng."""
    questions = [_name_question(rng.fork(1), first_name)]

    subject_count = rng.fork(2).randint(3, 4)
    chosen = _shuffle(rng.fork(3), SUBJECTS)[:subject_count]

    pool: list[dict] = []
    for subject in chosen:
        for q in QUESTIONS[subject]:
            pool.append({**q, "subject": subject})

    selected = _shuffle(rng.fork(4), pool)[:9]
    selected.sort(key=lambda q: q["difficulty"])
    questions.extend(selected)

    return {
        "questions": questions,
        "index": 0,
        "answers": [],
        "correct": 0,
        "caught": False,
        "finished": False,
        "revealed": None,  # answer index revealed by a successful cheat
    }


def grade_for(correct: int, total: int, smarts: int) -> str:
    """Blend exam performance with smarts and map to a letter grade."""
    if total <= 0:
        ratio = 0.0
    else:
        ratio = correct / total
    adjusted = ratio * 0.7 + (max(0, min(100, smarts)) / 100) * 0.3
    if adjusted >= 0.85:
        return "A"
    if adjusted >= 0.72:
        return "B"
    if adjusted >= 0.60:
        return "C"
    if adjusted >= 0.50:
        return "D"
    if adjusted >= 0.40:
        return "E"
    return "F"


def admission_for(grade: str) -> dict:
    """Map a grade to a university tier and scholarship offer."""
    return {
        "A": {"tier": "Prestigious", "scholarship": "full"},
        "B": {"tier": "Prestigious", "scholarship": "partial"},
        "C": {"tier": "Standard", "scholarship": "none"},
        "D": {"tier": "Standard", "scholarship": "none"},
        "E": {"tier": "Community", "scholarship": "none"},
        "F": {"tier": "", "scholarship": "none"},
    }.get(grade, {"tier": "", "scholarship": "none"})
