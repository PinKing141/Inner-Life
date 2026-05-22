"""Housing: renting, buying, selling and net worth.

Buying a home pays the full price now — which can push the bank balance
negative (treated like a mortgage/loan) and is paid back by income over time,
the same model used for student debt. Renting is a recurring yearly expense.
Owned property is an asset that drifts in value and counts toward net worth.
"""
from __future__ import annotations

from core.content import housing as housing_content
from core.rng import Rng
from core.state import GameState

MIN_HOUSING_AGE = 18


def _market(state: GameState) -> list[dict]:
    city = state.character.city if state.character else ""
    return housing_content.list_market(state.seed, city)


def list_market(state: GameState) -> list[dict]:
    return _market(state)


def net_worth(state: GameState) -> int:
    return state.money + sum(p.get("value", 0) for p in state.properties)


def annual_rent(state: GameState) -> int:
    return state.rental["rent"] if state.rental else 0


def buy_home(state: GameState, listing_id: str) -> tuple[bool, str]:
    if state.character is None:
        return False, "No character."
    if state.character.age < MIN_HOUSING_AGE:
        return False, "You're too young to buy a home."
    city = state.character.city
    listing = housing_content.find_listing(state.seed, city, listing_id)
    if listing is None:
        return False, "That property isn't on the market."
    if any(p["id"] == listing_id for p in state.properties):
        return False, "You already own that property."
    price = listing["price"]
    state.money -= price
    state.properties.append({
        "id": listing["id"],
        "name": listing["name"],
        "value": price,
        "purchase_price": price,
    })
    return True, f"You bought {listing['name']} for £{price:,}."


def rent_home(state: GameState, listing_id: str) -> tuple[bool, str]:
    if state.character is None:
        return False, "No character."
    if state.character.age < MIN_HOUSING_AGE:
        return False, "You're too young to rent a home."
    city = state.character.city
    listing = housing_content.find_listing(state.seed, city, listing_id)
    if listing is None:
        return False, "That property isn't on the market."
    state.rental = {"id": listing["id"], "name": listing["name"], "rent": listing["rent"]}
    return True, f"You moved into {listing['name']} for £{listing['rent']:,}/yr."


def stop_renting(state: GameState) -> tuple[bool, str]:
    if not state.rental:
        return False, "You aren't renting anywhere."
    name = state.rental["name"]
    state.rental = None
    return True, f"You moved out of {name}."


def sell_home(state: GameState, property_id: str) -> tuple[bool, str]:
    prop = next((p for p in state.properties if p["id"] == property_id), None)
    if prop is None:
        return False, "You don't own that property."
    value = prop.get("value", 0)
    state.money += value
    state.properties.remove(prop)
    return True, f"You sold {prop['name']} for £{value:,}."


def annual_update(state: GameState, rng: Rng) -> None:
    """Drift owned property values a little each year."""
    for i, prop in enumerate(state.properties):
        change = rng.fork(i + 1).randint(-2, 5) / 100.0
        prop["value"] = max(0, int(prop["value"] * (1 + change)))
