"""Simulation observatory.

NOT a gameplay feature — a systems-debugging tool. Runs many deterministic
lives and aggregates lifecycle + system-interaction metrics so emergent
imbalance (runaway loops, exploits, sterile stability) becomes visible by
observation rather than guesswork.

    python -m scripts.observe                 # default 300 lives per cohort
    python -m scripts.observe --lives 500
    python -m scripts.observe --trajectory 42 # dump one life's feed

The auto-play POLICY is an explicit assumption, kept deliberately simple so
it doesn't smuggle in balancing decisions:

  * Events are resolved by a per-life seeded RNG picking a random valid
    choice (avoids the bias of always taking choice 0).
  * PASSIVE cohort: never seeks work. Pure baseline pressure.
  * ACTIVE cohort: each year, if jobless and eligible, applies to the
    highest-salary non-criminal job whose hard requirements are met.
  * Neither cohort attends university, uses paid activities, or interacts
    with NPCs — we are observing the systems' *own* dynamics, not a
    strategy on top of them.

Comparing the two cohorts is the point: it isolates what employment changes
about poverty, isolation, bailouts and lifespan.
"""
from __future__ import annotations

import argparse
import statistics
from dataclasses import dataclass, field

from core import economy, sim
from core.content.jobs import JOBS, education_meets
from core.rng import Rng
from core.state import GameState

TALENTS = ["Academics", "Acting", "Sports"]
COUNTRIES = ["UK", "US", "JP", "NG", "BR"]
SEVERE_DEBT = -1000
LONELY_THRESHOLD = 25  # mirrors relationships.LONELY_THRESHOLD
CLOSE_KINDS = ("Mother", "Father", "Sibling", "Partner", "Friend")


# --------------------------------------------------------------------------
# Auto-play policy
# --------------------------------------------------------------------------

def _best_eligible_job(state: GameState):
    elig = []
    for j in JOBS:
        if j.track == "criminal":
            continue
        if state.character.age < j.min_age:
            continue
        if state.stats.smarts < j.min_smarts:
            continue
        if not education_meets(state.education.level, j.min_education):
            continue
        if j.required_field and (
            not state.education.degree_completed
            or state.education.degree_field != j.required_field
        ):
            continue
        elig.append(j)
    return max(elig, key=lambda j: j.salary) if elig else None


def _support(state: GameState) -> int:
    """Strongest surviving close tie (0 if fully isolated)."""
    close = [r.relationship for r in state.relationships if r.alive and r.kind in CLOSE_KINDS]
    return max(close, default=0)


# --------------------------------------------------------------------------
# Per-life record
# --------------------------------------------------------------------------

@dataclass
class LifeRecord:
    seed: int
    age_at_death: int = 0
    employed_years: int = 0
    unemployed_adult_years: int = 0
    years_in_debt: int = 0
    years_severe_debt: int = 0
    isolation_years: int = 0
    bailouts: int = 0
    recovered_after_bailout: bool = False
    final_money: int = 0
    min_money: int = 0
    final_support: int = 0
    avg_support: float = 0.0
    avg_happiness: float = 0.0
    avg_health: float = 0.0
    parent_min_money: int = 0
    parents_drained: int = 0  # parents ending at £0
    living_close_at_death: int = 0


def run_life(seed: int, *, active: bool) -> LifeRecord:
    talent = TALENTS[seed % len(TALENTS)]
    country = COUNTRIES[(seed // len(TALENTS)) % len(COUNTRIES)]
    gender = ("Male", "Female", "NonBinary")[seed % 3]
    state = sim.new_game(seed=seed, name="", gender=gender, country=country, talent=talent)
    state.education.university_intent = "skip"

    choice_rng = Rng(seed ^ 0x5EED)
    rec = LifeRecord(seed=seed)
    supports: list[int] = []
    happies: list[int] = []
    healths: list[int] = []
    last_bailout_tick = -1
    solvent_after_bailout = False

    guard = 0
    while state.mode == "PLAYING" and guard < 130:
        guard += 1
        if state.pending_event_id is not None:
            ev = sim.get_pending_event(state)
            n = len(ev["choices"]) if ev else 1
            sim.resolve_choice(state, choice_rng.randint(0, max(0, n - 1)))
            continue
        if active and state.career is None and state.character.age >= 16:
            job = _best_eligible_job(state)
            if job is not None:
                economy.apply_for_job(state, job.job_id)

        prev_bailouts = sum(1 for f in state.feed if f.entry_id.startswith("feed:help:"))
        sim.age_up(state)

        age = state.character.age
        if age >= 18:
            if state.career is not None:
                rec.employed_years += 1
            else:
                rec.unemployed_adult_years += 1
        if state.money < 0:
            rec.years_in_debt += 1
        if state.money < SEVERE_DEBT:
            rec.years_severe_debt += 1
        sup = _support(state)
        supports.append(sup)
        if sup < LONELY_THRESHOLD:
            rec.isolation_years += 1
        happies.append(state.stats.happiness)
        healths.append(state.stats.health)
        rec.min_money = min(rec.min_money, state.money)

        now_bailouts = sum(1 for f in state.feed if f.entry_id.startswith("feed:help:"))
        if now_bailouts > prev_bailouts:
            last_bailout_tick = state.tick
        if last_bailout_tick >= 0 and state.tick > last_bailout_tick and state.money >= 0:
            solvent_after_bailout = True

    rec.age_at_death = state.character.age
    rec.bailouts = sum(1 for f in state.feed if f.entry_id.startswith("feed:help:"))
    rec.recovered_after_bailout = solvent_after_bailout
    rec.final_money = state.money
    rec.final_support = supports[-1] if supports else 0
    rec.avg_support = statistics.mean(supports) if supports else 0.0
    rec.avg_happiness = statistics.mean(happies) if happies else 0.0
    rec.avg_health = statistics.mean(healths) if healths else 0.0
    parent_money = [a.money for a in state.agents if a.role in ("Mother", "Father")]
    rec.parent_min_money = min(parent_money, default=0)
    rec.parents_drained = sum(1 for m in parent_money if m <= 0)
    rec.living_close_at_death = sum(
        1 for r in state.relationships if r.alive and r.kind in CLOSE_KINDS
    )
    return rec


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------

def _mean(xs):
    return statistics.mean(xs) if xs else 0.0


def _split_compare(records, key_fn, value_fn, label):
    """Split records at the median of key_fn, compare mean value_fn per half."""
    keyed = sorted(records, key=key_fn)
    if len(keyed) < 4:
        return f"  {label}: not enough data"
    mid = len(keyed) // 2
    low, high = keyed[:mid], keyed[mid:]
    lo_k, hi_k = _mean([key_fn(r) for r in low]), _mean([key_fn(r) for r in high])
    lo_v, hi_v = _mean([value_fn(r) for r in low]), _mean([value_fn(r) for r in high])
    return f"  {label}: low-group({lo_k:.1f})→{lo_v:,.0f}   high-group({hi_k:.1f})→{hi_v:,.0f}"


def report_cohort(name: str, records: list[LifeRecord]) -> None:
    n = len(records)
    print(f"\n{'='*70}\n{name} cohort  (n={n})\n{'='*70}")

    print("Life trajectory")
    print(f"  age at death           : mean {_mean([r.age_at_death for r in records]):.1f}  "
          f"min {min(r.age_at_death for r in records)}  max {max(r.age_at_death for r in records)}")
    print(f"  avg happiness (life)   : {_mean([r.avg_happiness for r in records]):.1f}")
    print(f"  avg health (life)      : {_mean([r.avg_health for r in records]):.1f}")

    print("Economy")
    print(f"  employed adult-years   : {_mean([r.employed_years for r in records]):.1f}")
    print(f"  unemployed adult-years : {_mean([r.unemployed_adult_years for r in records]):.1f}")
    print(f"  years in debt          : {_mean([r.years_in_debt for r in records]):.1f}")
    print(f"  years in severe debt   : {_mean([r.years_severe_debt for r in records]):.1f}")
    print(f"  final money            : mean £{_mean([r.final_money for r in records]):,.0f}  "
          f"min £{min(r.min_money for r in records):,}")

    print("Generosity / bailouts")
    total_bailouts = sum(r.bailouts for r in records)
    with_bailout = [r for r in records if r.bailouts > 0]
    print(f"  total bailouts         : {total_bailouts}  "
          f"({len(with_bailout)}/{n} lives received >=1)")
    if with_bailout:
        print(f"  recovered to solvency after a bailout : "
              f"{sum(1 for r in with_bailout if r.recovered_after_bailout)}/{len(with_bailout)}")
        print(f"  death age: bailout-receivers {_mean([r.age_at_death for r in with_bailout]):.1f} "
              f"vs others {_mean([r.age_at_death for r in records if r.bailouts == 0]):.1f}")
    print(f"  parents ending at £0   : {sum(r.parents_drained for r in records)} "
          f"(avg min parent money £{_mean([r.parent_min_money for r in records]):,.0f})")

    print("Social")
    print(f"  isolation years        : {_mean([r.isolation_years for r in records]):.1f}")
    print(f"  avg support (life)     : {_mean([r.avg_support for r in records]):.1f}")
    print(f"  living close ties at death : {_mean([r.living_close_at_death for r in records]):.2f}")

    print("System interactions")
    print(_split_compare(records, lambda r: r.isolation_years, lambda r: r.final_money,
                         "isolation_years -> final_money (do isolated people get poorer?)"))
    print(_split_compare(records, lambda r: r.unemployed_adult_years, lambda r: r.isolation_years,
                         "unemployment -> isolation_years (does joblessness cascade?)"))
    print(_split_compare(records, lambda r: r.years_severe_debt, lambda r: float(r.bailouts),
                         "severe_debt_years -> bailouts (does hardship pull in help?)"))


def dump_trajectory(seed: int, active: bool) -> None:
    talent = TALENTS[seed % len(TALENTS)]
    country = COUNTRIES[(seed // len(TALENTS)) % len(COUNTRIES)]
    gender = ("Male", "Female", "NonBinary")[seed % 3]
    state = sim.new_game(seed=seed, name="", gender=gender, country=country, talent=talent)
    state.education.university_intent = "skip"
    choice_rng = Rng(seed ^ 0x5EED)
    guard = 0
    while state.mode == "PLAYING" and guard < 130:
        guard += 1
        if state.pending_event_id is not None:
            ev = sim.get_pending_event(state)
            n = len(ev["choices"]) if ev else 1
            sim.resolve_choice(state, choice_rng.randint(0, max(0, n - 1)))
            continue
        if active and state.career is None and state.character.age >= 16:
            job = _best_eligible_job(state)
            if job is not None:
                economy.apply_for_job(state, job.job_id)
        sim.age_up(state)
    print(f"\nTrajectory seed={seed} ({'active' if active else 'passive'}), "
          f"{state.character.name}, died at {state.character.age}\n{'-'*70}")
    for f in state.feed:
        print(f"  age {f.age:>3} [{f.kind:<7}] {f.text}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lives", type=int, default=300)
    ap.add_argument("--trajectory", type=int, default=None,
                    help="dump one life's full feed instead of running cohorts")
    ap.add_argument("--passive-trajectory", action="store_true",
                    help="with --trajectory, use the passive policy")
    args = ap.parse_args()

    if args.trajectory is not None:
        dump_trajectory(args.trajectory, active=not args.passive_trajectory)
        return

    passive = [run_life(s, active=False) for s in range(args.lives)]
    active = [run_life(s, active=True) for s in range(args.lives)]
    report_cohort("PASSIVE (never works)", passive)
    report_cohort("ACTIVE (seeks best eligible job)", active)


if __name__ == "__main__":
    main()
