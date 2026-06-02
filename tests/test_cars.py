"""Cars / Assets v1 — buy, depreciate, sell, save/load, net-worth fold-in.

Covers the catalogue contract, all three refusal modes for buy_car,
depreciation floor + jitter determinism, the OwnsAVehicle predicate,
heir-transition reset, and integration with housing.net_worth.
"""
from __future__ import annotations

import pytest

from controller.game_controller import GameController
from core import cars, housing, sim
from core.predicates import OwnsAVehicle
from core.rng import Rng
from core.state import GameState


def _new(seed: int = 1, age: int = 25, money: int = 100_000) -> GameState:
    s = sim.new_game(seed=seed, name="", gender="Female", country="US", talent="Sports")
    s.character.age = age
    s.money = money
    return s


# --- Catalogue invariants -------------------------------------------------


def test_catalogue_has_required_fields():
    """Every car must have the keys the engine/UI reads. Guards against
    a half-added entry crashing the snapshot."""
    required = ("name", "brand", "model", "price", "top_speed", "prestige",
                "min_age", "depreciation_rate", "blurb")
    for car_id, c in cars.CARS.items():
        for key in required:
            assert key in c, f"{car_id} missing {key}"
        assert c["price"] > 0
        assert 0 < c["depreciation_rate"] < 1
        assert c["min_age"] >= 16


def test_catalogue_is_priced_in_ladder_order():
    """The dict declaration order implicitly defines the ladder. If
    someone reorders entries without updating prices, this catches it."""
    prices = [c["price"] for c in cars.CARS.values()]
    assert prices == sorted(prices), "catalogue prices must increase"


# --- buy_car refusals -----------------------------------------------------


def test_buy_car_unknown_id_refuses_cleanly():
    s = _new()
    ok, msg = cars.buy_car(s, "spaceship")
    assert ok is False
    assert s.money == 100_000  # untouched
    assert s.vehicles == []


def test_buy_car_under_age_refuses():
    s = _new(age=15)  # below all min_ages
    ok, _ = cars.buy_car(s, "used_hatchback")
    assert ok is False
    assert s.vehicles == []


def test_buy_car_broke_refuses():
    s = _new(money=100)
    ok, _ = cars.buy_car(s, "commuter_sedan")  # costs £18k
    assert ok is False
    assert s.money == 100
    assert s.vehicles == []


# --- buy_car happy path ---------------------------------------------------


def test_buy_car_debits_money_and_appends_vehicle():
    s = _new()
    ok, _ = cars.buy_car(s, "commuter_sedan")
    assert ok is True
    assert s.money == 100_000 - 18_000
    assert len(s.vehicles) == 1
    v = s.vehicles[0]
    assert v["car_id"] == "commuter_sedan"
    assert v["current_value"] == 18_000
    assert v["age_years"] == 0
    assert v["instance_id"] >= 1


def test_buy_two_cars_assigns_distinct_instance_ids():
    s = _new(money=200_000)
    cars.buy_car(s, "used_hatchback")
    cars.buy_car(s, "used_hatchback")
    ids = [v["instance_id"] for v in s.vehicles]
    assert len(set(ids)) == 2


# --- Depreciation ---------------------------------------------------------


def test_annual_depreciation_reduces_value():
    s = _new()
    cars.buy_car(s, "luxury_sedan")  # rate 0.12
    initial = s.vehicles[0]["current_value"]
    cars.annual_depreciation(s, Rng(1).fork(7))
    after = s.vehicles[0]["current_value"]
    # Depreciation rate 0.12 ± 0.02 jitter → at least 10% off.
    assert after < initial
    assert after > int(initial * 0.80)  # not more than 20% off in one year


def test_depreciation_floors_at_purchase_fraction():
    """After enough years a car cannot depreciate below 10% of price."""
    s = _new()
    cars.buy_car(s, "sport_compact")  # price 55k, rate 12%
    for i in range(50):
        cars.annual_depreciation(s, Rng(i + 1).fork(7))
    v = s.vehicles[0]
    floor = int(v["purchase_price"] * cars.VALUE_FLOOR_FRACTION)
    assert v["current_value"] == floor


def test_depreciation_advances_age_years():
    s = _new()
    cars.buy_car(s, "used_hatchback")
    for i in range(5):
        cars.annual_depreciation(s, Rng(i).fork(7))
    assert s.vehicles[0]["age_years"] == 5


def test_depreciation_is_deterministic_under_same_rng():
    s1 = _new(money=200_000)
    s2 = _new(money=200_000)
    cars.buy_car(s1, "sports_car")
    cars.buy_car(s2, "sports_car")
    rng_seed = 12345
    for _ in range(5):
        cars.annual_depreciation(s1, Rng(rng_seed).fork(7))
        cars.annual_depreciation(s2, Rng(rng_seed).fork(7))
        rng_seed += 1
    assert s1.vehicles[0]["current_value"] == s2.vehicles[0]["current_value"]


# --- sell_car -------------------------------------------------------------


def test_sell_car_credits_current_value_and_removes_vehicle():
    s = _new()
    cars.buy_car(s, "luxury_sedan")
    instance_id = s.vehicles[0]["instance_id"]
    money_before = s.money
    cars.annual_depreciation(s, Rng(1).fork(7))
    value_now = s.vehicles[0]["current_value"]
    ok, _ = cars.sell_car(s, instance_id)
    assert ok is True
    assert s.money == money_before + value_now
    assert s.vehicles == []


def test_sell_car_unknown_instance_refuses():
    s = _new()
    ok, _ = cars.sell_car(s, 999_999)
    assert ok is False


# --- Predicate ------------------------------------------------------------


def test_owns_a_vehicle_predicate():
    s = _new()
    assert OwnsAVehicle()(s) is False
    cars.buy_car(s, "used_hatchback")
    assert OwnsAVehicle()(s) is True


# --- Net-worth integration -----------------------------------------------


def test_housing_net_worth_includes_vehicle_value():
    s = _new(money=100_000)
    base = housing.net_worth(s)
    assert base == 100_000  # no property, no cars
    cars.buy_car(s, "luxury_sedan")  # -£65k from money, +£65k from vehicle
    after = housing.net_worth(s)
    assert after == base  # net worth unchanged immediately after purchase
    # After depreciation, net worth dips by the depreciation amount.
    cars.annual_depreciation(s, Rng(1).fork(7))
    after_depr = housing.net_worth(s)
    assert after_depr < after


# --- Save / load ---------------------------------------------------------


def test_vehicles_roundtrip_through_save_load():
    s = _new()
    cars.buy_car(s, "sports_car")
    cars.annual_depreciation(s, Rng(7).fork(7))
    rebuilt = GameState.from_dict(s.to_dict())
    assert rebuilt.vehicles == s.vehicles


# --- Sim integration -----------------------------------------------------


def test_age_up_runs_depreciation_in_free_world():
    s = _new(seed=42)
    cars.buy_car(s, "family_suv")
    value_before = s.vehicles[0]["current_value"]
    sim.age_up(s)
    if s.pending_event_id:
        sim.resolve_choice(s, 0)
    assert s.vehicles[0]["current_value"] < value_before


def test_age_up_skips_depreciation_during_incarceration():
    """Cars sit in storage while the player is inside — no depreciation."""
    s = _new(seed=42)
    cars.buy_car(s, "family_suv")
    value_before = s.vehicles[0]["current_value"]
    s.crime.is_incarcerated = True
    s.crime.sentence_years = 5
    sim.age_up(s)
    if s.pending_event_id:
        sim.resolve_choice(s, 0)
    assert s.vehicles[0]["current_value"] == value_before


# --- Heir transition -----------------------------------------------------


def test_continue_as_heir_resets_vehicles():
    from core import genealogy
    from core.agents import Agent
    from core.state import Relationship
    s = _new(seed=99)
    s.relationships.append(Relationship(
        npc_id=900, name="P", kind="Partner", relationship=80, alive=True,
    ))
    s.agents.append(Agent(
        npc_id=900, first_name="P", last_name="X", gender="NonBinary",
        role="Partner", age=30, country=s.character.country, city="",
    ))
    cars.buy_car(s, "supercar")
    genealogy.begin_pregnancy(s)
    s.tick += 1
    # Walk a healthy birth so we can continue.
    for seed in range(30):
        result = genealogy.resolve_pregnancy(s, Rng(seed).fork(7))
        if result is not None:
            break
    if not s.character.children:
        pytest.skip("no healthy birth in seed range; flaky fixture only")
    heir_id = s.character.children[0]
    s.mode = "DEATH"
    genealogy.continue_as_heir(s, heir_id)
    assert s.vehicles == []


# --- Controller verbs ----------------------------------------------------


def test_controller_buy_car_and_snapshot_exposes_market():
    c = GameController()
    c.new_game(seed=1, name="", gender="Female", country="US", talent="Sports")
    c.state.character.age = 25
    c.state.money = 100_000
    snap = c.buy_car("commuter_sedan")
    assert any(v["car_id"] == "commuter_sedan" for v in snap["vehicles"])
    assert "car_market" in snap
    # market includes catalogue with availability flags
    cs = next(r for r in snap["car_market"] if r["id"] == "commuter_sedan")
    assert "success_chance" not in cs  # this isn't crime — sanity
    assert cs["price"] == 18_000


def test_controller_sell_car_credits_money():
    c = GameController()
    c.new_game(seed=2, name="", gender="Male", country="US", talent="Sports")
    c.state.character.age = 25
    c.state.money = 100_000
    c.buy_car("used_hatchback")
    instance_id = c.state.vehicles[0]["instance_id"]
    money_before = c.state.money
    c.sell_car(instance_id)
    assert c.state.money > money_before
    assert c.state.vehicles == []
