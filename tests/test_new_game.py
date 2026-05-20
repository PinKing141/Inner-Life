from __future__ import annotations

from core import sim


def test_new_game_starts_with_zero_money():
    state = sim.new_game(seed=123, name="A", gender="Male", country="UK", talent="Sports")
    assert state.money == 0
