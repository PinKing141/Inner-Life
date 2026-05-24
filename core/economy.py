"""Economy: career, salary, living costs.

The annual budget pass runs from core.sim.tick. This module just declares the
rules for whether a job application succeeds and what the yearly cashflow
looks like.
"""
from __future__ import annotations

from core import balance
from core.content.jobs import JOBS, JobSpec, education_meets
from core.rng import Rng
from core.state import GameState, Job

JOB_FAMILY_STABILITY: dict[str, float] = {
    "doctor": 0.35,
    "teacher": 0.25,
    "developer": 0.10,
    "retail_worker": -0.25,
    "delivery_driver": -0.10,
}

# Promotion ladder: a rank prefix is added to the profession as the player
# climbs. Index 0 is the entry-level title.
RANK_PREFIX = ["", "Senior ", "Lead ", "Principal ", "Chief "]
MAX_LEVEL = len(RANK_PREFIX) - 1

_EMPLOYER_PATTERNS = [
    "{city} {noun}", "{noun} Group", "{noun} & Partners",
    "{city} {noun} Co.", "United {noun}", "{noun} International",
]
_EMPLOYER_NOUNS = [
    "Holdings", "Solutions", "Industries", "Systems", "Logistics",
    "Associates", "Enterprises", "Ventures", "Works", "Trading",
]


def list_jobs() -> list[JobSpec]:
    return JOBS


def find_job(job_id: str) -> JobSpec | None:
    for j in JOBS:
        if j.job_id == job_id:
            return j
    return None


def employer_for(state: GameState, job_id: str) -> str:
    """A stable employer name for a given job listing (same seed + job_id)."""
    salt = sum(ord(c) for c in job_id)
    rng = Rng(state.seed).fork(salt * 13 + 5)
    city = (state.character.city if state.character else "") or "City"
    noun = rng.choice(_EMPLOYER_NOUNS)
    return rng.choice(_EMPLOYER_PATTERNS).format(city=city, noun=noun)


def profession_for(spec: JobSpec) -> str:
    return spec.career or spec.title


def max_level_for(spec: JobSpec) -> int:
    return (len(spec.ladder) - 1) if spec.ladder else MAX_LEVEL


def rung_title(spec: JobSpec, level: int) -> str:
    if spec.ladder:
        level = max(0, min(len(spec.ladder) - 1, level))
        return spec.ladder[level]
    level = max(0, min(MAX_LEVEL, level))
    return f"{RANK_PREFIX[level]}{profession_for(spec)}".strip()


def apply_for_job(state: GameState, job_id: str) -> tuple[bool, str]:
    """Returns (hired, message). State is mutated only on success.

    Every rejection sets ``state.job_application_error`` so the UI can surface
    a dedicated "you were rejected" popup with the reason.
    """
    def reject(msg: str) -> tuple[bool, str]:
        state.job_application_error = msg
        return False, msg

    if state.character is None:
        return False, "No character."
    spec = find_job(job_id)
    if spec is None:
        return False, "That job does not exist."
    if state.character.age < spec.min_age:
        return reject(f"You are too young to be a {spec.title}.")
    if state.stats.smarts < spec.min_smarts:
        return reject(f"You failed the interview for {spec.title}. You need to be smarter.")
    if not education_meets(state.education.level, spec.min_education):
        return reject(f"You need at least {spec.min_education} to be a {spec.title}.")

    # Degree-gated professions hard-reject anyone without the right field.
    if spec.required_field:
        edu = state.education
        if not edu.degree_completed or edu.degree_field != spec.required_field:
            return reject(
                f"Your application to be a {spec.title} was rejected — "
                f"they require a degree in {spec.required_field.replace('_', ' ')}."
            )

    # Even when you meet every requirement, a hire isn't guaranteed.
    salt = sum(ord(c) for c in job_id)
    rng = Rng(state.seed).fork(state.tick).fork(salt)
    hire_chance = 0.9 if spec.required_field else 0.85
    if not rng.chance(hire_chance):
        return reject(f"You interviewed for {spec.title} but weren't offered the role this time.")

    employer = employer_for(state, job_id)
    profession = profession_for(spec)
    title = rung_title(spec, 0)
    state.career = Job(
        job_id=spec.job_id,
        title=title,
        salary=spec.salary,
        employer=employer,
        career=profession,
        level=0,
        performance=50,
    )
    state.job_application_error = None
    state.stats.happiness = min(100, state.stats.happiness + balance.HAPPY_HIRE_DELTA)
    state.pending_job_offer = {
        "title": title,
        "career": profession,
        "employer": employer,
        "salary": spec.salary,
    }
    return True, f"You were hired as a {title} at {employer}. Your salary is £{spec.salary:,}."


def work_harder(state: GameState) -> str:
    """Push for a promotion. Raises job performance at a small happiness cost."""
    if state.career is None:
        return "You don't have a job to work at."
    state.career.performance = min(100, state.career.performance + 8)
    state.stats.happiness = max(0, state.stats.happiness - 2)
    return "You put in extra hours at work. Your performance improved."


def quit_job(state: GameState) -> str:
    """Player resigns. Clears the career."""
    if state.career is None:
        return "You don't have a job to quit."
    title = state.career.title
    state.career = None
    return f"You quit your job as a {title}."


def request_raise(state: GameState) -> tuple[bool, str]:
    """Ask the boss for a raise. One ask per year; refusal annoys the boss."""
    job = state.career
    if job is None:
        return False, "You don't have a job."
    if job.last_ask_tick == state.tick:
        return False, "You've already spoken to your boss this year."
    job.last_ask_tick = state.tick
    rng = Rng(state.seed).fork(state.tick).fork(777)
    chance = max(0.05, min(0.9, 0.2 + (job.performance - 50) / 100.0))
    if rng.fork(1).chance(chance):
        pct = rng.fork(2).randint(5, 12)
        job.salary = int(job.salary * (1 + pct / 100.0))
        return True, f"Your boss approved a {pct}% raise! You now earn £{job.salary:,}."
    job.performance = max(0, job.performance - 5)
    return False, "Your boss turned down your request for a raise."


def request_promotion(state: GameState) -> tuple[bool, str, dict | None]:
    """Ask the boss for a promotion. Needs decent performance; refusal stings."""
    job = state.career
    if job is None:
        return False, "You don't have a job.", None
    spec = find_job(job.job_id)
    max_level = max_level_for(spec) if spec else MAX_LEVEL
    if job.level >= max_level:
        return False, "You're already at the top of your field.", None
    if job.last_ask_tick == state.tick:
        return False, "You've already spoken to your boss this year.", None
    job.last_ask_tick = state.tick
    rng = Rng(state.seed).fork(state.tick).fork(778)
    chance = max(0.05, min(0.85, (job.performance - 55) / 60.0))
    if rng.fork(1).chance(chance):
        old_salary = job.salary
        pct = rng.fork(2).randint(10, 20)
        job.level += 1
        job.salary = int(old_salary * (1 + pct / 100.0))
        job.title = rung_title(spec, job.level) if spec else job.title
        job.performance = 55
        promo = {
            "type": "promotion",
            "title": job.title,
            "career": job.career,
            "employer": job.employer,
            "salary": job.salary,
            "pct": pct,
        }
        return True, f"You asked for a promotion — and got it!", promo
    job.performance = max(0, job.performance - 5)
    return False, "Your boss declined to promote you this time.", None


def career_tick(state: GameState, rng: Rng) -> dict | None:
    """Run a year of career progression.

    Returns an outcome dict — {"type": "promotion"|"layoff"} — or None.
    A layoff/firing clears the career; the caller surfaces the popup.
    """
    job = state.career
    if job is None or state.character is None:
        return None
    spec = find_job(job.job_id)
    world = state.world.clamped()

    # Performance drifts down if you coast.
    job.performance = max(0, job.performance - rng.fork(1).randint(0, 4))

    # Morale has authority over work, as a CONTINUOUS gradient around a neutral
    # 50 rather than a switch — so mid-range mood matters too and there are no
    # stepwise cliffs. Kept deliberately small (~±2/yr) so happiness refines
    # career trajectories without becoming a second master variable.
    mood_bias = (state.stats.happiness - 50) / 25.0  # ~ -2 .. +2
    jitter = rng.fork(9).uniform(-0.5, 0.5)
    job.performance = max(0, min(100, job.performance + round(mood_bias + jitter)))

    # --- Job loss check (recession layoffs + poor performance) ---
    stability = JOB_FAMILY_STABILITY.get(job.job_id, 0.0)
    layoff_risk = 0.0
    reason = ""
    if world.recession:
        layoff_risk += 0.06 + max(0.0, world.unemployment_rate - 0.05) * 0.6
        reason = "company downsizing during the recession"
    layoff_risk = max(0.0, layoff_risk - stability * 0.1)
    fired_for_performance = job.performance < 25
    if fired_for_performance:
        layoff_risk += 0.20
        reason = "poor performance"
    if layoff_risk > 0 and rng.fork(4).chance(layoff_risk):
        former = {
            "type": "layoff",
            "title": job.title,
            "career": job.career,
            "employer": job.employer,
            "reason": reason or "redundancy",
            "fired": fired_for_performance,
        }
        state.career = None
        return former

    # --- Demotion: weak (but not catastrophic) performance costs a rank ---
    if job.level > 0 and job.performance < 45:
        if rng.fork(5).chance((45 - job.performance) / 100.0):
            old_salary = job.salary
            job.level -= 1
            job.title = rung_title(spec, job.level) if spec else job.title
            pct = rng.fork(6).randint(8, 18)
            job.salary = int(old_salary * (1 - pct / 100.0))
            job.performance = 50
            return {
                "type": "demotion",
                "title": job.title,
                "career": job.career,
                "employer": job.employer,
                "old_salary": old_salary,
                "salary": job.salary,
                "pct": pct,
                "reason": "poor performance",
            }

    # --- Pay cut: recessions squeeze salaries without costing the role ---
    if world.recession and rng.fork(7).chance(0.08):
        old_salary = job.salary
        pct = rng.fork(8).randint(5, 12)
        job.salary = int(old_salary * (1 - pct / 100.0))
        return {
            "type": "paycut",
            "title": job.title,
            "career": job.career,
            "employer": job.employer,
            "old_salary": old_salary,
            "salary": job.salary,
            "pct": pct,
            "reason": "salary cut during the recession",
        }

    # --- Promotion check ---
    max_level = max_level_for(spec) if spec else MAX_LEVEL
    if job.level >= max_level or job.performance < 70:
        return None
    promote_chance = (job.performance - 60) / 100.0
    if not rng.fork(2).chance(promote_chance):
        return None

    old_salary = job.salary
    pct = rng.fork(3).randint(10, 20)
    job.level += 1
    job.salary = int(old_salary * (1 + pct / 100.0))
    job.title = rung_title(spec, job.level) if spec else job.title
    job.performance = 55
    return {
        "type": "promotion",
        "title": job.title,
        "career": job.career,
        "employer": job.employer,
        "salary": job.salary,
        "pct": pct,
    }


def annual_cashflow(state: GameState, rng: Rng) -> tuple[int, int, str]:
    """Returns (earnings, living_cost, note). State is NOT mutated."""
    if state.character is None or state.character.age < 18:
        return 0, 0, ""
    world = state.world.clamped()
    inflation = world.inflation_index

    base_living = 5_000 + rng.randint(0, 2_000)
    recession_penalty = 600 if world.recession else 0
    subsistence = int((base_living + recession_penalty) * inflation)
    if state.rental:
        subsistence += state.rental.get("rent", 0)

    if state.career:
        stability = JOB_FAMILY_STABILITY.get(state.career.job_id, 0.0)
        unemployment_risk = max(0.0, world.unemployment_rate - 0.04)
        salary_hit = min(0.40, max(0.0, unemployment_risk * (1.6 - stability) + (0.12 if world.recession else 0.0) - (0.05 * stability)))
        earnings = int(state.career.salary * (1.0 - salary_hit))
        # Lifestyle creep: spending rises with income, so net saving is only a
        # fraction of disposable income. This is the friction that converts the
        # accumulation funnel into income-proportional savings — a real middle
        # band, and high earners who are far less infinitely-cushioned. It does
        # NOT equalise: the rich still save more in absolute terms.
        disposable = max(0, earnings - subsistence)
        living_cost = subsistence + int(balance.LIFESTYLE_CREEP * disposable)
        note = f"You earned £{earnings:,} from your job in a {'recession' if world.recession else 'volatile'} economy."
    else:
        pressure = int(400 * inflation) + (500 if world.recession else 0)
        earnings = -pressure
        living_cost = subsistence  # no lifestyle creep without an income
        note = "You are unemployed and struggling in a weak economy."

    return earnings, max(0, living_cost), note
