"""Central balance knobs.

The single home for the cross-cutting tuning constants that previously lived
as inline literals across sim.py and economy.py. The point is not aesthetic
centralisation but a *tuning surface*: a future balance pass should touch
this file, not archaeology across modules. Locally well-named constants that
sit next to their own logic (HELP_* in agents, PARTNER_*, LONELY_*) are kept
there to preserve cohesion — only the unnamed scattered numbers move here.

Values are unchanged from the inline literals they replace.
"""
from __future__ import annotations

# --- Happiness deltas for discrete life events ----------------------------
HAPPY_HIRE_DELTA = 5
HAPPY_PROMOTION_DELTA = 6
HAPPY_LAYOFF_DELTA = -12
HAPPY_SETBACK_DELTA = -6   # demotion or pay-cut
HAPPY_DEBT_DELTA = -6
HAPPY_NO_JOB_DELTA = -5
HAPPY_ANNUAL_DRIFT_MAX = 3  # passed to rng.randint(0, MAX)

# --- Debt -> health erosion curve -----------------------------------------
# Health only erodes under deep debt (below threshold), and only stochastically
# with a depth-scaled chance. See core/sim.py for the call site.
DEBT_HEALTH_THRESHOLD = -8_000
DEBT_HEALTH_DEPTH_DIVISOR = 40_000  # how fast severity ramps with debt depth
DEBT_HEALTH_BASE_CHANCE = 0.15
DEBT_HEALTH_DEPTH_BONUS = 0.40      # added to base at maximum depth (1.0)

# --- Economy ---------------------------------------------------------------
# Fraction of disposable income consumed by lifestyle creep — the friction
# that stops wealth being a one-direction accumulation funnel.
LIFESTYLE_CREEP = 0.80
