"""Determinism guard.

Same seed + same inputs == same outputs. If this test ever fails, something
in the core picked up nondeterministic randomness (global random, datetime,
dict iteration order, etc.) and needs to be tracked down.
"""
from __future__ import annotations

from core import sim


def test_same_seed_same_run():
    a = sim.new_game(seed=42, name="A", gender="Male", country="UK", talent="Sports")
    b = sim.new_game(seed=42, name="A", gender="Male", country="UK", talent="Sports")
    assert a.stats == b.stats
    assert a.money == b.money

    for _ in range(20):
        sim.age_up(a)
        sim.age_up(b)
        # resolve any pending events identically by always picking choice 0
        if a.pending_event_id is not None:
            sim.resolve_choice(a, 0)
        if b.pending_event_id is not None:
            sim.resolve_choice(b, 0)

    assert a.stats == b.stats
    assert a.money == b.money
    assert len(a.feed) == len(b.feed)
    assert [f.text for f in a.feed] == [f.text for f in b.feed]


def test_different_seeds_diverge():
    a = sim.new_game(seed=1, name="A", gender="Male", country="UK", talent="Sports")
    b = sim.new_game(seed=999, name="A", gender="Male", country="UK", talent="Sports")
    for _ in range(40):
        sim.age_up(a)
        sim.age_up(b)
        if a.pending_event_id is not None:
            sim.resolve_choice(a, 0)
        if b.pending_event_id is not None:
            sim.resolve_choice(b, 0)
    # They might *coincidentally* match on small numbers, but their feeds will diverge
    a_log = [f.text for f in a.feed]
    b_log = [f.text for f in b.feed]
    assert a_log != b_log, "Two different seeds produced identical lives; determinism broken in the wrong direction."


def test_same_seed_same_university_transition_snapshot():
    a = sim.new_game(seed=123, name="A", gender="Male", country="UK", talent="Sports")
    b = sim.new_game(seed=123, name="A", gender="Male", country="UK", talent="Sports")
    a.education.university_intent = "attend"
    a.education.university_major = "Physics"
    b.education.university_intent = "attend"
    b.education.university_major = "Physics"

    while a.character and a.character.age < 18:
        sim.age_up(a)
        sim.age_up(b)
        if a.pending_event_id is not None:
            sim.resolve_choice(a, 0)
        if b.pending_event_id is not None:
            sim.resolve_choice(b, 0)

    assert a.education == b.education
    assert [f.text for f in a.feed] == [f.text for f in b.feed]
