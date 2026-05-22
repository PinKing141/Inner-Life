"""Distribution regression guards for emergent structure.

Unit tests prove the systems *execute*; these guard that the system keeps
producing a *healthy spread of life-types*. They assert bands, not exact
values — the point is to fail loudly if a future change accidentally:

  * re-binarises outcomes (one archetype dominates),
  * collapses variance (everyone converges),
  * resurrects a master variable, or
  * kills off an archetype.

Bands are deliberately wide around the sim-equilibrium-v1 baseline so normal
drift doesn't trip them; only structural collapse should.
"""
from __future__ import annotations

import statistics
from collections import Counter

import pytest

from scripts.observe import run_life, _econ_archetype, _social_archetype

N = 200


@pytest.fixture(scope="module")
def cohort():
    return [run_life(s, active=True) for s in range(N)]


def _share(records, classify):
    counts = Counter(classify(r) for r in records)
    return {k: v / len(records) for k, v in counts.items()}


def test_economic_archetypes_stay_diverse(cohort):
    share = _share(cohort, _econ_archetype)
    # A real middle class exists, hardship is bounded, and no single economic
    # identity swallows the population (anti re-binarisation).
    assert 0.10 <= share.get("stable-middle", 0) <= 0.45, share
    assert share.get("chronic-debt", 0) <= 0.45, share
    assert share.get("early-decline", 0) <= 0.15, share
    assert max(share.values()) <= 0.55, share


def test_social_archetypes_stay_diverse(cohort):
    share = _share(cohort, _social_archetype)
    # Isolation persists as a real minority; no social identity dominates.
    assert share.get("isolated", 0) >= 0.03, share
    assert max(share.values()) <= 0.75, share


def test_partnership_prevalence_bounded(cohort):
    prevalence = sum(1 for r in cohort if r.ever_partnered) / len(cohort)
    # Catch both collapse directions: nobody pairs up, or it becomes universal.
    assert 0.40 <= prevalence <= 0.99, prevalence


def test_variance_has_not_collapsed(cohort):
    # Outcomes must remain spread — money and lifespan are not converging to a
    # single attractor.
    wealth_sd = statistics.pstdev([r.final_money for r in cohort])
    age_sd = statistics.pstdev([r.age_at_death for r in cohort])
    assert wealth_sd >= 50_000, wealth_sd
    assert age_sd >= 4.0, age_sd


def test_no_axis_is_sovereign_over_lifespan(cohort):
    # Death age must retain a real spread (not a deterministic clock or a single
    # immortal band).
    ages = [r.age_at_death for r in cohort]
    assert max(ages) - min(ages) >= 20, (min(ages), max(ages))
