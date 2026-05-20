"""Smoke tests for the event subsystem."""
from __future__ import annotations

from core import sim
from core.events import get_event


def test_get_event_known_id():
    assert get_event("found_money") is not None


def test_get_event_missing_id():
    assert get_event("does_not_exist") is None


def test_event_resolution_writes_feed():
    state = sim.new_game(seed=7, name="A", gender="Male", country="UK", talent="Music")
    # Force a pending event manually so we exercise resolve_choice.
    state.pending_event_id = "found_money"
    before = len(state.feed)
    sim.resolve_choice(state, 0)
    assert len(state.feed) == before + 1
    assert state.pending_event_id is None
    # The first choice for found_money grants £20.
    assert state.money >= 20


def test_age_progresses_only_when_no_pending_event():
    state = sim.new_game(seed=11, name="A", gender="Male", country="UK", talent="Crime")
    state.pending_event_id = "found_money"
    age_before = state.character.age
    sim.age_up(state)
    assert state.character.age == age_before, "age_up must block on a pending event"


def test_causal_chain_records_choice():
    state = sim.new_game(seed=3, name="A", gender="Female", country="UK", talent="Acting")
    state.pending_event_id = "found_money"
    sim.resolve_choice(state, 0)
    assert any(c["kind"] == "event_choice" for c in state.causal_chain)
