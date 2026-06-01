"""Phase 6 — milestone modals.

Milestones (18, 30, 50, 65, 100) must fire deterministically the year the
player turns that age, must not double-fire, must reset across an heir
transition, and must survive a save/load round-trip.
"""
from __future__ import annotations

from controller.game_controller import GameController
from core import genealogy, milestones, sim
from core.rng import Rng
from core.state import GameState, Relationship


def _new(seed: int = 1) -> GameState:
    return sim.new_game(seed=seed, name="", gender="Female", country="US", talent="Sports")


def test_milestone_fires_on_threshold_age():
    s = _new()
    s.character.age = 18
    queued = milestones.check(s)
    assert queued is not None
    assert s.pending_milestone is not None
    assert s.pending_milestone["age"] == 18
    assert 18 in s.milestones_seen


def test_milestone_does_not_fire_on_non_threshold():
    s = _new()
    s.character.age = 19
    assert milestones.check(s) is None
    assert s.pending_milestone is None


def test_milestone_only_fires_once_per_age():
    s = _new()
    s.character.age = 30
    milestones.check(s)
    milestones.acknowledge(s)
    # Same age, second tick — must not re-queue.
    assert milestones.check(s) is None
    assert s.pending_milestone is None


def test_milestone_check_refuses_to_overwrite_pending():
    """If the player hasn't dismissed the previous milestone, a new one
    cannot displace it. (Realistic age gaps make this rare but the
    invariant matters for save/load and stale state.)"""
    s = _new()
    s.character.age = 18
    milestones.check(s)
    assert s.pending_milestone["age"] == 18
    # Pretend they aged a decade without acknowledging.
    s.character.age = 30
    assert milestones.check(s) is None
    assert s.pending_milestone["age"] == 18  # still the original


def test_milestone_resets_on_heir_transition():
    """Each new generation gets their own 18, 30, etc. The heir's life
    must start with milestones_seen empty and no pending."""
    from core.agents import Agent
    s = _new(seed=42)
    s.relationships.append(Relationship(
        npc_id=900, name="Pat", kind="Partner", relationship=80, alive=True,
    ))
    s.agents.append(Agent(
        npc_id=900, first_name="Pat", last_name="X", gender="NonBinary",
        role="Partner", age=30, country="United States", city="",
    ))
    genealogy.have_child(s, Rng(99).fork(7))
    heir_id = s.character.children[0]
    s.character.age = 65
    milestones.check(s)
    assert 65 in s.milestones_seen
    s.mode = "DEATH"
    genealogy.continue_as_heir(s, heir_id)
    assert s.pending_milestone is None
    assert s.milestones_seen == []


def test_milestone_survives_save_load_roundtrip():
    s = _new()
    s.character.age = 50
    milestones.check(s)
    rebuilt = GameState.from_dict(s.to_dict())
    assert rebuilt.pending_milestone == s.pending_milestone
    assert rebuilt.milestones_seen == s.milestones_seen


def test_acknowledge_clears_pending():
    s = _new()
    s.character.age = 100
    milestones.check(s)
    assert s.pending_milestone is not None
    milestones.acknowledge(s)
    assert s.pending_milestone is None
    # milestones_seen retains the record — won't re-fire.
    assert 100 in s.milestones_seen


def test_controller_verb_clears_milestone():
    c = GameController()
    c.new_game(seed=1, name="", gender="Male", country="US", talent="Sports")
    c.state.character.age = 18
    milestones.check(c.state)
    snap = c.snapshot()
    assert snap["pending_milestone"] is not None
    snap2 = c.acknowledge_milestone()
    assert snap2["pending_milestone"] is None


def test_sim_age_up_queues_milestone_at_18():
    """End-to-end: age a character to 17, tick once, and the 18 milestone
    must be queued by sim — not require the event roll to surface it."""
    s = _new(seed=7)
    s.character.age = 17
    while s.pending_event_id is not None:
        s.pending_event_id = None
    sim.age_up(s)
    assert s.character.age == 18
    # The milestone must be queued regardless of which random event rolled.
    assert s.pending_milestone is not None
    assert s.pending_milestone["age"] == 18
