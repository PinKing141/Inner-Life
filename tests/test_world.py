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

    assert bad[0] < good[0]
    assert bad[1] > good[1]


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
