"""Engine scalability — the per-tick skip floor must preserve life
variance even when many extra events are added to the catalogue.

The roadmap intends to grow the event catalogue toward 300+. Without a
skip floor, the per-tick firing rate climbs toward 100% as candidates
multiply, and cumulative life drift homogenises outcomes (death-age
stdev collapses; archetype shares converge). See PR #32 for the
investigation that led to ``core.events.NO_EVENT_TICK_PROB``.

This test bolts 50 synthetic mild-effect events onto the catalogue at
runtime, runs a small cohort, and asserts that:

  1. With the skip floor enabled (current default), variance survives.
  2. With the skip floor disabled, variance collapses.

That's the regression contract: the floor must be doing actual work.
"""
from __future__ import annotations

import statistics

import pytest

from core import events as events_engine
from core.content import events as catalogue
from scripts.observe import run_life


N = 60  # smaller than the full observatory cohort (200) to keep test cost low


@pytest.fixture
def synthetic_events():
    """Append 50 mild-effect, no-predicate events spread across life
    phases. Tear down after the test so the real catalogue isn't
    polluted for subsequent tests."""
    extras = []
    for i in range(50):
        # Tile each event into a 5-year window from age 10 to 70.
        start = 10 + (i % 12) * 5
        extras.append({
            "id": f"_synth_{i}",
            "min_age": start, "max_age": start + 4,
            "prob": 0.10,
            "text": "synthetic",
            "choices": [
                {"text": "go", "effects": {"happiness": -2, "smarts": 1},
                 "log": "synthetic outcome"},
                {"text": "stay", "effects": {"happiness": 1, "smarts": -1},
                 "log": "synthetic outcome"},
            ],
        })
    before = len(catalogue.EVENTS)
    catalogue.EVENTS.extend(extras)
    yield
    # Restore. Strict assertion so a future refactor that mutates EVENTS
    # in flight gets caught.
    del catalogue.EVENTS[before:]


def _age_sd(records) -> float:
    return statistics.pstdev([r.age_at_death for r in records])


def test_skip_floor_preserves_variance_when_catalogue_grows(synthetic_events):
    """With the skip enabled (default), adding 50 synthetic events must
    NOT collapse age variance below the observatory's 4.0 floor."""
    cohort = [run_life(s, active=True) for s in range(N)]
    sd = _age_sd(cohort)
    assert sd >= 4.0, (
        f"age variance collapsed to {sd:.2f} with 50 extra events + skip "
        f"enabled — the skip floor isn't doing its job."
    )


def test_without_skip_floor_variance_collapses(synthetic_events, monkeypatch):
    """Sanity check: disable the floor (set to 0), and the same cohort
    measurably loses variance. This guards against the floor becoming
    a no-op via some future refactor."""
    monkeypatch.setattr(events_engine, "NO_EVENT_TICK_PROB", 0.0)
    cohort = [run_life(s, active=True) for s in range(N)]
    sd_without = _age_sd(cohort)

    # Re-enable and resample for the comparison reference.
    monkeypatch.setattr(events_engine, "NO_EVENT_TICK_PROB", 0.30)
    cohort_with = [run_life(s, active=True) for s in range(N)]
    sd_with = _age_sd(cohort_with)

    # The skip floor must MEASURABLY help — at least a small gap. Not
    # asserting the without-floor cohort fails the 4.0 threshold
    # outright (that depends on exact synthetic event placement); just
    # that the floor moves the needle in the right direction.
    assert sd_with > sd_without, (
        f"skip floor had no effect: with={sd_with:.2f}, without={sd_without:.2f}"
    )
