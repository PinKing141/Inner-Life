from __future__ import annotations

from core import legend, sim


def _build_state_with_two_events(seed: int = 21):
    state = sim.new_game(seed=seed, name="A", gender="Female", country="UK", talent="Acting")
    state.pending_event_id = "found_money"
    sim.resolve_choice(state, 0)
    state.pending_event_id = "found_money"
    sim.resolve_choice(state, 1)
    return state


def test_legend_uses_structured_event_choice_fields():
    state = _build_state_with_two_events()
    out = legend.read_legend(state)
    assert out["items"], "Expected at least one cause node"
    head = out["items"][0]
    assert head["kind"] == "event_choice"
    assert head["event_id"] == "found_money"
    assert head["schema_version"] == 1
    assert head["source"] == "events.resolve_choice"


def test_legend_records_parent_link_for_event_choices():
    state = _build_state_with_two_events()
    latest = state.causal_chain[-1]
    assert latest["parent_id"] == state.causal_chain[-2]["id"]


def test_legend_output_is_deterministic_for_same_seed_and_actions():
    a = _build_state_with_two_events(seed=99)
    b = _build_state_with_two_events(seed=99)
    assert legend.read_legend(a) == legend.read_legend(b)
