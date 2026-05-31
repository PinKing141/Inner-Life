"""Housing catalogue and market generation.

A small set of property types scaled from a studio flat to a mansion. The
market shown to the player is generated per city (deterministically from the
seed) with a little price variation, so two cities don't look identical.

A richer property system (mortgages, neighbourhoods, upkeep, market crashes)
is a natural later extension; this is the first, simple pass.
"""
from __future__ import annotations

from typing import cast

from core.rng import Rng

# Base price (buy) and annual rent for each property type.
PROPERTY_TYPES = [
    {"key": "studio",    "name": "Studio Flat",          "price": 85_000,    "rent": 7_200},
    {"key": "flat1",     "name": "1-Bed Apartment",      "price": 140_000,   "rent": 9_600},
    {"key": "terrace",   "name": "Terraced House",       "price": 240_000,   "rent": 13_200},
    {"key": "semi",      "name": "Semi-Detached House",  "price": 340_000,   "rent": 16_800},
    {"key": "detached",  "name": "Detached House",       "price": 520_000,   "rent": 22_800},
    {"key": "penthouse", "name": "Luxury Penthouse",     "price": 1_200_000, "rent": 48_000},
    {"key": "mansion",   "name": "Mansion",              "price": 3_500_000, "rent": 120_000},
]


def list_market(seed: int, city: str) -> list[dict]:
    """A stable per-city market listing (same seed + city -> same listings)."""
    city = city or "City"
    salt = sum(ord(c) for c in city)
    market = []
    for i, t in enumerate(PROPERTY_TYPES):
        rng = Rng(seed).fork(salt * 31 + i)
        variation = 1.0 + rng.randint(-12, 12) / 100.0
        # PROPERTY_TYPES holds mixed-type values, so the price/rent read back as
        # `object`; narrow to int for the arithmetic.
        price = int(cast(int, t["price"]) * variation)
        rent = int(cast(int, t["rent"]) * variation)
        market.append({
            "id": f"{t['key']}-{salt}",
            "key": t["key"],
            "name": t["name"],
            "price": price,
            "rent": rent,
        })
    return market


def find_listing(seed: int, city: str, listing_id: str) -> dict | None:
    for listing in list_market(seed, city):
        if listing["id"] == listing_id:
            return listing
    return None
