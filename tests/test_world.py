from __future__ import annotations

import math

from core import sim
from core.economy import annual_cashflow
from core.legend import read_legend
from core.rng import Rng
from core.state import GameState


def _advance_years(state: GameState, years: int) -> None:
    for _ in range(years):
        sim.age_up(state)
        if state.pending_event_id is not None:
            sim.resolve_choice(state, 0)


def test_world_trajectory_same_seed_identical():
    a = sim.new_game(seed=77, name="A", gender="Male", country="UK", talent="Sports")
    b = sim.new_game(seed=77, name="A", gender="Male", country="UK", talent="Sports")
    _advance_years(a, 20)
    _advance_years(b, 20)
    assert a.world.to_dict() == b.world.to_dict()


def test_world_trajectory_different_seed_diverges():
    a = sim.new_game(seed=10, name="A", gender="Male", country="UK", talent="Sports")
    b = sim.new_game(seed=11, name="A", gender="Male", country="UK", talent="Sports")
    _advance_years(a, 20)
    _advance_years(b, 20)
    assert a.world.to_dict() != b.world.to_dict()


def test_economy_world_coupling_changes_outcomes():
    s = sim.new_game(seed=5, name="A", gender="Female", country="UK", talent="Sports")
    while s.character and s.character.age < 18:
        sim.age_up(s)
        if s.pending_event_id is not None:
            sim.resolve_choice(s, 0)
    from core.state import Job
    s.career = Job("dev", "Developer", 50_000)

    s.world.inflation_index = 1.0
    s.world.unemployment_rate = 0.03
    s.world.recession = False
    good = annual_cashflow(s, Rng(123).fork(7))

    s.world.inflation_index = 1.25
    s.world.unemployment_rate = 0.16
    s.world.recession = True
    bad = annual_cashflow(s, Rng(123).fork(7))

    # A worse economy earns less, and (with lifestyle creep) leaves less net
    # savings — earnings - living_cost. Gross outflow can fall in a downturn
    # because discretionary lifestyle spending tracks income; net is the real
    # coupling.
    assert bad[0] < good[0]
    assert (bad[0] - bad[1]) < (good[0] - good[1])


def test_world_invariants_hold_over_time():
    s = sim.new_game(seed=90, name="A", gender="Female", country="US", talent="Acting")
    _advance_years(s, 40)
    assert 0.0 <= s.world.unemployment_rate <= 1.0
    assert s.world.inflation_index >= 0.5
    assert math.isfinite(s.world.inflation_index)
    assert math.isfinite(s.world.unemployment_rate)


def test_world_cause_nodes_surface_in_legend():
    s = sim.new_game(seed=1, name="A", gender="Female", country="US", talent="Acting")
    # advance until a world transition cause is emitted
    for _ in range(25):
        sim.age_up(s)
        if s.pending_event_id is not None:
            sim.resolve_choice(s, 0)
        if any(f.cause_id and f.cause_id.startswith("world:") for f in s.feed):
            break
    target = next((f for f in reversed(s.feed) if f.cause_id and f.cause_id.startswith("world:")), None)
    assert target is not None
    legend = read_legend(s, target.entry_id)
    assert legend["items"]
    assert legend["items"][0]["id"].startswith("world:")

def test_world_long_horizon_recovery_and_stability():
    s = sim.new_game(seed=222, name="A", gender="Female", country="US", talent="Acting")
    saw_recession = False
    saw_recovery = False
    for _ in range(100):
        was_recession = s.world.recession
        sim.age_up(s)
        if s.pending_event_id is not None:
            sim.resolve_choice(s, 0)
        saw_recession = saw_recession or s.world.recession or was_recession
        if was_recession and not s.world.recession:
            saw_recovery = True
        assert 0.0 <= s.world.unemployment_rate <= 1.0
        assert s.world.unemployment_rate < 0.30
        assert 0.5 <= s.world.inflation_index <= 3.0
    assert saw_recession
    assert saw_recovery
