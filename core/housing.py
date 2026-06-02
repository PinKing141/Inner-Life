"""Housing: renting, buying, selling and net worth.

Buying a home pays the full price now — which can push the bank balance
negative (treated like a mortgage/loan) and is paid back by income over time,
the same model used for student debt. Renting is a recurring yearly expense.
Owned property is an asset that drifts in value and counts toward net worth.
"""
from __future__ import annotations

from core.content import housing as housing_content
from core.results import ActionResult
from core.rng import Rng
from core.state import GameState

MIN_HOUSING_AGE = 18
MORTGAGE_RATE = 0.05      # annual interest
MORTGAGE_TERM = 25        # years
MORTGAGE_DOWN_PCT = 0.10  # deposit as a fraction of price


def _annual_payment(principal: int, rate: float, years: int) -> int:
    if years <= 0:
        return principal
    if rate == 0:
        return round(principal / years)
    factor = (1 + rate) ** years
    return round(principal * rate * factor / (factor - 1))


def _market(state: GameState) -> list[dict]:
    city = state.character.city if state.character else ""
    return housing_content.list_market(state.seed, city)


def list_market(state: GameState) -> list[dict]:
    return _market(state)


def net_worth(state: GameState) -> int:
    # Cars/Assets v1: vehicles are a second asset class. Local import
    # avoids a circular dependency at module load — core.cars itself
    # doesn't need housing.
    from core import cars
    return (
        state.money
        + sum(p.get("value", 0) - p.get("mortgage_balance", 0) for p in state.properties)
        + cars.total_value(state)
    )


def annual_mortgage_outgoings(state: GameState) -> int:
    return sum(p.get("mortgage_payment", 0) for p in state.properties if p.get("mortgage_balance", 0) > 0)


def annual_rent(state: GameState) -> int:
    return state.rental["rent"] if state.rental else 0


def _can_buy(state: GameState, listing_id: str):
    if state.character is None:
        return None, "No character."
    if state.character.age < MIN_HOUSING_AGE:
        return None, "You're too young to buy a home."
    listing = housing_content.find_listing(state.seed, state.character.city, listing_id)
    if listing is None:
        return None, "That property isn't on the market."
    if any(p["id"] == listing_id for p in state.properties):
        return None, "You already own that property."
    return listing, ""


def buy_home(state: GameState, listing_id: str) -> ActionResult:
    """Buy outright — pays the full price now."""
    listing, err = _can_buy(state, listing_id)
    if listing is None:
        return ActionResult(False, err)
    price = listing["price"]
    state.money -= price
    state.properties.append({
        "id": listing["id"],
        "name": listing["name"],
        "value": price,
        "purchase_price": price,
        "mortgage_balance": 0,
        "mortgage_payment": 0,
        "mortgage_rate": 0.0,
        "mortgage_term_left": 0,
    })
    return ActionResult(True, f"You bought {listing['name']} outright for £{price:,}.")


def buy_home_mortgage(state: GameState, listing_id: str) -> ActionResult:
    """Buy with a mortgage — a deposit now, then annual payments."""
    listing, err = _can_buy(state, listing_id)
    if listing is None:
        return ActionResult(False, err)
    price = listing["price"]
    deposit = int(price * MORTGAGE_DOWN_PCT)
    if state.money < deposit:
        return ActionResult(False, f"You can't afford the £{deposit:,} deposit.")
    principal = price - deposit
    payment = _annual_payment(principal, MORTGAGE_RATE, MORTGAGE_TERM)
    state.money -= deposit
    state.properties.append({
        "id": listing["id"],
        "name": listing["name"],
        "value": price,
        "purchase_price": price,
        "mortgage_balance": principal,
        "mortgage_payment": payment,
        "mortgage_rate": MORTGAGE_RATE,
        "mortgage_term_left": MORTGAGE_TERM,
    })
    monthly = payment // 12
    return ActionResult(True, (
        f"You bought {listing['name']} with a mortgage — £{deposit:,} deposit, "
        f"about £{monthly:,}/month."
    ))


def rent_home(state: GameState, listing_id: str) -> ActionResult:
    if state.character is None:
        return ActionResult(False, "No character.")
    if state.character.age < MIN_HOUSING_AGE:
        return ActionResult(False, "You're too young to rent a home.")
    city = state.character.city
    listing = housing_content.find_listing(state.seed, city, listing_id)
    if listing is None:
        return ActionResult(False, "That property isn't on the market.")
    state.rental = {"id": listing["id"], "name": listing["name"], "rent": listing["rent"]}
    return ActionResult(True, f"You moved into {listing['name']} for £{listing['rent']:,}/yr.")


def stop_renting(state: GameState) -> ActionResult:
    if not state.rental:
        return ActionResult(False, "You aren't renting anywhere.")
    name = state.rental["name"]
    state.rental = None
    return ActionResult(True, f"You moved out of {name}.")


def sell_home(state: GameState, property_id: str) -> ActionResult:
    prop = next((p for p in state.properties if p["id"] == property_id), None)
    if prop is None:
        return ActionResult(False, "You don't own that property.")
    value = prop.get("value", 0)
    balance = prop.get("mortgage_balance", 0)
    proceeds = value - balance
    state.money += proceeds
    state.properties.remove(prop)
    if balance > 0:
        return ActionResult(True, f"You sold {prop['name']} for £{value:,}, settling the £{balance:,} mortgage.")
    return ActionResult(True, f"You sold {prop['name']} for £{value:,}.")


def annual_update(state: GameState, rng: Rng) -> None:
    """Drift owned property values and make mortgage payments each year."""
    for i, prop in enumerate(state.properties):
        change = rng.fork(i + 1).randint(-2, 5) / 100.0
        prop["value"] = max(0, int(prop["value"] * (1 + change)))

        balance = prop.get("mortgage_balance", 0)
        if balance > 0:
            rate = prop.get("mortgage_rate", MORTGAGE_RATE)
            balance = balance * (1 + rate)  # interest accrues
            payment = min(prop.get("mortgage_payment", 0), balance)
            balance -= payment
            state.money -= int(round(payment))
            prop["mortgage_balance"] = max(0, int(round(balance)))
            prop["mortgage_term_left"] = max(0, prop.get("mortgage_term_left", 0) - 1)
            if prop["mortgage_balance"] <= 0:
                prop["mortgage_payment"] = 0
