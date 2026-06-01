"""Phase 6 — extended activity catalogue.

Smoke + invariant coverage for the new activity verbs. Tests the things
that would silently break if a refactor went wrong: every descriptor has
a matching BY_KIND entry, every BY_KIND entry returns the (ok, log) shape,
gated activities (cost / relationship) fail cleanly with a useful reason,
and successful activities mutate stats within the 0..100 clamp.
"""
from __future__ import annotations

import pytest

from core import activities, sim
from core.state import GameState, Relationship


def _new(seed: int = 1) -> GameState:
    return sim.new_game(seed=seed, name="", gender="Female", country="US", talent="Sports")


def test_descriptor_and_dispatch_tables_are_in_sync():
    """Every UI descriptor must map to a real verb, and every verb must
    surface to the UI — otherwise the player taps a button that no-ops,
    or a working verb is unreachable."""
    descriptor_ids = {d["id"] for d in activities.DESCRIPTORS}
    dispatch_ids = set(activities.BY_KIND.keys())
    assert descriptor_ids == dispatch_ids, (
        f"unmatched: in descriptors only={descriptor_ids - dispatch_ids}, "
        f"in dispatch only={dispatch_ids - descriptor_ids}"
    )


def test_every_activity_returns_ok_log_tuple():
    """Defensive: any function added to BY_KIND must follow the contract."""
    s = _new()
    s.money = 100_000  # so cost-gated ones can succeed
    # Seed minimal relationships so the relationship-gated verbs can run.
    s.relationships.append(Relationship(
        npc_id=901, name="Pal", kind="Friend", relationship=70, alive=True,
    ))
    s.relationships.append(Relationship(
        npc_id=902, name="Lover", kind="Partner", relationship=80, alive=True,
    ))
    for kind, fn in activities.BY_KIND.items():
        result = fn(s)
        assert isinstance(result, tuple) and len(result) == 2, kind
        ok, log = result
        assert isinstance(ok, bool), kind
        assert isinstance(log, str) and log, kind


@pytest.mark.parametrize("kind,cost", [
    ("gym", activities.GYM_COST),
    ("doctor", activities.DOCTOR_COST),
    ("therapy", activities.THERAPY_COST),
    ("haircut", activities.HAIRCUT_COST),
    ("tattoo", activities.TATTOO_COST),
    ("cosmetic_surgery", activities.COSMETIC_COST),
    ("vacation", activities.VACATION_COST),
    ("party", activities.PARTY_COST),
    ("night_at_the_bar", activities.BAR_COST),
    ("healthy_diet", activities.DIET_COST),
    ("spa_day", activities.SPA_COST),
])
def test_cost_gated_activities_refuse_when_broke(kind, cost):
    s = _new()
    s.money = cost - 1
    ok, log = activities.BY_KIND[kind](s)
    assert ok is False
    assert "afford" in log.lower()
    assert s.money == cost - 1  # state untouched on refusal


def test_call_mother_refuses_when_no_living_mother():
    s = _new()
    # Kill any auto-spawned Mother relationship.
    for r in s.relationships:
        if r.kind == "Mother":
            r.alive = False
    ok, log = activities.call_mother(s)
    assert ok is False
    assert "mother" in log.lower()


def test_hang_with_friends_refuses_without_friend():
    s = _new()
    s.relationships = [r for r in s.relationships if r.kind != "Friend"]
    ok, log = activities.hang_with_friends(s)
    assert ok is False


def test_date_night_refuses_without_partner_even_with_money():
    s = _new()
    s.money = 10_000
    s.relationships = [r for r in s.relationships if r.kind != "Partner"]
    ok, log = activities.date_night(s)
    assert ok is False
    assert "partner" in log.lower()


def test_date_night_bumps_partner_relationship_score():
    s = _new()
    s.money = 1_000
    partner = Relationship(npc_id=999, name="Lover", kind="Partner",
                           relationship=50, alive=True)
    s.relationships.append(partner)
    ok, _ = activities.date_night(s)
    assert ok is True
    assert partner.relationship == 55  # +5 bump


def test_volunteer_is_free_and_boosts_happiness():
    s = _new()
    s.money = 0
    s.stats.happiness = 50  # default 100 would be clamp-pinned
    starting_happy = s.stats.happiness
    ok, _ = activities.volunteer(s)
    assert ok is True
    assert s.money == 0
    assert s.stats.happiness > starting_happy


def test_side_gig_pays_real_money():
    s = _new()
    starting = s.money
    activities.side_gig(s)
    assert s.money == starting + 60


def test_stats_stay_clamped_after_repeated_activity_calls():
    """1000 spa days should not push looks above 100 or money negative
    silently — clamps are the only thing keeping the sim sane."""
    s = _new()
    s.money = 1_000_000
    for _ in range(1000):
        activities.spa_day(s)
    assert 0 <= s.stats.happiness <= 100
    assert 0 <= s.stats.looks <= 100
    assert 0 <= s.stats.health <= 100
