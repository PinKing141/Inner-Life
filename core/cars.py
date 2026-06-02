"""Cars / vehicles v1.

A second asset class beyond housing. Where homes appreciate slowly,
cars depreciate fast — the model has to differ. v1 ships:

- A declarative 8-vehicle ladder (used hatchback through hypercar) with
  prices, age gates, and per-vehicle depreciation rates.
- ``state.vehicles`` — a list of owned-vehicle dicts with their own
  ``instance_id`` so the player can pick which one to sell.
- ``annual_depreciation`` runs each free-world tick (skipped during
  incarceration, like the event roll, since the car sits in storage).
- ``total_value`` aggregates current market value across all owned
  vehicles; housing.net_worth folds this into the player's total wealth.

State machine
-------------

::

    no car ──buy_car(car_id)──▶ owned ──annual_depreciation──▶ worth less
              ▲                                                    │
              └─────────────sell_car(instance_id)──────────────────┘

Determinism
-----------

The depreciation roll has small RNG jitter (±2 percentage points) so
two identical cars bought in the same year diverge slightly over time —
a forked Rng off the tick keeps this reproducible per seed.

Why per-vehicle current_value (instead of computing from age + rate at
read time)?
- The catalogue can be retuned (new cars added, prices adjusted) without
  rewriting every player's owned-vehicle value retroactively.
- The annual depreciation tick is the single point where value moves,
  so reading the value is O(1) per vehicle.
"""
from __future__ import annotations

from core.rng import Rng
from core.state import FeedEntry, GameState


# Declarative catalogue. Each entry is a complete recipe — the engine
# never special-cases by id. ``depreciation_rate`` is annual; the value
# floor (10% of purchase price) prevents the car from going to literal
# zero so trade-in always means something.
CARS: dict[str, dict] = {
    "used_hatchback": {
        "name": "Used Hatchback",
        "brand": "Ford", "model": "Fiesta (used)",
        "price": 3_000, "top_speed": 110, "prestige": 0,
        "min_age": 17,
        "depreciation_rate": 0.08,
        "blurb": "A first car. Cheap, honest, faintly embarrassing.",
    },
    "commuter_sedan": {
        "name": "Commuter Sedan",
        "brand": "Toyota", "model": "Corolla",
        "price": 18_000, "top_speed": 130, "prestige": 5,
        "min_age": 17,
        "depreciation_rate": 0.10,
        "blurb": "Reliable, anonymous, the spreadsheet's pick.",
    },
    "family_suv": {
        "name": "Family SUV",
        "brand": "Honda", "model": "CR-V",
        "price": 28_000, "top_speed": 130, "prestige": 10,
        "min_age": 17,
        "depreciation_rate": 0.10,
        "blurb": "Roomy enough for prams, dogs, regret.",
    },
    "sport_compact": {
        "name": "Sport Compact",
        "brand": "BMW", "model": "M2",
        "price": 55_000, "top_speed": 165, "prestige": 25,
        "min_age": 21,
        "depreciation_rate": 0.12,
        "blurb": "Quick. Mean. The badge says quite a lot.",
    },
    "luxury_sedan": {
        "name": "Luxury Sedan",
        "brand": "Mercedes-Benz", "model": "E-Class",
        "price": 65_000, "top_speed": 155, "prestige": 30,
        "min_age": 21,
        "depreciation_rate": 0.12,
        "blurb": "Soft leather, silent miles. A grown-up choice.",
    },
    "sports_car": {
        "name": "Sports Car",
        "brand": "Porsche", "model": "911",
        "price": 110_000, "top_speed": 190, "prestige": 50,
        "min_age": 25,
        "depreciation_rate": 0.15,
        "blurb": "The one your teenage self folded into magazines.",
    },
    "supercar": {
        "name": "Supercar",
        "brand": "Lamborghini", "model": "Huracán",
        "price": 280_000, "top_speed": 200, "prestige": 80,
        "min_age": 25,
        "depreciation_rate": 0.15,
        "blurb": "It's not subtle. It's not pretending to be.",
    },
    "hypercar": {
        "name": "Hypercar",
        "brand": "Bugatti", "model": "Chiron",
        "price": 3_000_000, "top_speed": 250, "prestige": 100,
        "min_age": 28,
        "depreciation_rate": 0.20,
        "blurb": "A statement so large it has its own postcode.",
    },
}

VALUE_FLOOR_FRACTION = 0.10  # car never depreciates below 10% of purchase price


# --- Helpers --------------------------------------------------------------


def _next_instance_id(state: GameState) -> int:
    """Per-vehicle id so the player can target a specific car. Stepping
    past everything currently owned avoids collisions on save/load."""
    return max((v.get("instance_id", 0) for v in state.vehicles), default=0) + 1


def _find_vehicle(state: GameState, instance_id: int) -> dict | None:
    return next((v for v in state.vehicles if v.get("instance_id") == instance_id), None)


def _value_floor(purchase_price: int) -> int:
    return int(purchase_price * VALUE_FLOOR_FRACTION)


# --- Catalogue / UI -------------------------------------------------------


def list_market(state: GameState) -> list[dict]:
    """JSON-friendly catalogue rows for the UI. Includes per-row
    availability based on age + money so the UI can grey out rows."""
    out: list[dict] = []
    age = state.character.age if state.character else 0
    for car_id, c in CARS.items():
        meets_age = age >= c["min_age"]
        can_afford = state.money >= c["price"]
        out.append({
            "id": car_id,
            "name": c["name"],
            "brand": c["brand"],
            "model": c["model"],
            "price": c["price"],
            "top_speed": c["top_speed"],
            "prestige": c["prestige"],
            "min_age": c["min_age"],
            "blurb": c["blurb"],
            "available": meets_age and can_afford,
            "lock_reason": (
                None if meets_age and can_afford
                else "too young" if not meets_age
                else "can't afford"
            ),
        })
    return out


def list_owned(state: GameState) -> list[dict]:
    """JSON-friendly view of state.vehicles for the Assets UI."""
    return [dict(v) for v in state.vehicles]


def total_value(state: GameState) -> int:
    """Sum of current values across all owned vehicles. Read by
    housing.net_worth to compute the player's total wealth."""
    return sum(v.get("current_value", 0) for v in state.vehicles)


# --- Verbs ----------------------------------------------------------------


def buy_car(state: GameState, car_id: str) -> tuple[bool, str]:
    """Purchase a vehicle from the catalogue. Debits money, appends a
    new owned-vehicle dict. Refuses politely on unknown id, under-age,
    insufficient money. Doesn't refuse for "you already own one" —
    multiple cars are fine.
    """
    car = CARS.get(car_id)
    if car is None:
        return False, "That car isn't on the lot."
    if state.character is None or not state.character.alive:
        return False, "You can't buy a car right now."
    if state.character.age < car["min_age"]:
        return False, f"You need to be {car['min_age']} to drive this off the lot."
    if state.money < car["price"]:
        return False, f"You can't afford a {car['name']} (£{car['price']:,})."

    state.money -= car["price"]
    instance_id = _next_instance_id(state)
    state.vehicles.append({
        "instance_id": instance_id,
        "car_id": car_id,
        "name": car["name"],
        "brand": car["brand"],
        "model": car["model"],
        "purchase_price": car["price"],
        "current_value": car["price"],   # depreciation starts from next annual tick
        "age_years": 0,
        "depreciation_rate": car["depreciation_rate"],
    })
    return True, f"You bought a {car['brand']} {car['model']} for £{car['price']:,}."


def sell_car(state: GameState, instance_id: int) -> tuple[bool, str]:
    """Sell a specific owned vehicle. Credits its current market value
    to ``state.money``. Refuses on unknown instance_id."""
    vehicle = _find_vehicle(state, instance_id)
    if vehicle is None:
        return False, "You don't own that car."
    value = vehicle.get("current_value", 0)
    state.money += value
    state.vehicles = [v for v in state.vehicles if v is not vehicle]
    return True, f"Sold the {vehicle['brand']} {vehicle['model']} for £{value:,}."


# --- Tick -----------------------------------------------------------------


def annual_depreciation(state: GameState, rng: Rng) -> None:
    """Apply one year of depreciation to every owned vehicle. Called
    from sim.age_up in free-world ticks only — incarceration freezes
    the cars in their storage state.

    Each vehicle's current_value is multiplied by (1 - rate ± small
    jitter), then floored at ``VALUE_FLOOR_FRACTION`` of the purchase
    price so trade-in always returns something.
    """
    for i, v in enumerate(state.vehicles):
        v["age_years"] = v.get("age_years", 0) + 1
        rate = v.get("depreciation_rate", 0.10)
        jitter = rng.fork(i + 1).randint(-2, 2) / 100.0  # ±2 percentage points
        factor = 1.0 - max(0.0, min(0.50, rate + jitter))
        new_value = int(v.get("current_value", v.get("purchase_price", 0)) * factor)
        floor = _value_floor(v.get("purchase_price", 0))
        v["current_value"] = max(floor, new_value)


def write_depreciation_summary(state: GameState) -> str | None:
    """Optional feed line summarising the year's depreciation if it was
    significant (>£1,000 total). Returns None when no vehicles or trivial."""
    if not state.vehicles:
        return None
    total_now = sum(v.get("current_value", 0) for v in state.vehicles)
    total_paid = sum(v.get("purchase_price", 0) for v in state.vehicles)
    if total_paid == 0:
        return None
    return None  # Reserved for v2 — quiet by default to avoid feed spam.
