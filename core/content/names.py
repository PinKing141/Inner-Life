"""Country- and gender-aware name pools.

Backed by `_names_data.py`, generated from the bundled CSVs by
`scripts/build_name_data.py`. Lookups are by ISO-2 country code OR display
name. NonBinary draws are an interleave of the M and F pools so they read as
"a name from that culture" rather than defaulting to a single gender.
"""
from __future__ import annotations

from typing import Iterable

from core.content import countries as _countries
from core.content._names_data import FORENAMES as _FORENAMES_RAW
from core.content._names_data import SURNAMES as _SURNAMES_RAW

# UI-facing constants (kept for backwards compatibility with the legacy UI).
COUNTRIES = [c.name for c in _countries.list_countries()]
TALENTS = ["Sports", "Music", "Academics", "Crime", "Acting"]
GENDERS = ["Male", "Female", "NonBinary"]


def _gender_key(gender: str) -> str | None:
    """Map UI gender into the CSV's M/F code."""
    g = gender.strip().lower()
    if g in ("m", "male", "man", "boy"):
        return "M"
    if g in ("f", "female", "woman", "girl"):
        return "F"
    return None  # NonBinary or anything else


def _country_code(country: str) -> str:
    return _countries.resolve(country).code


def _interleave(a: Iterable[str], b: Iterable[str]) -> list[str]:
    """Round-robin merge preserving order from both pools."""
    out: list[str] = []
    ai = iter(a)
    bi = iter(b)
    while True:
        try:
            out.append(next(ai))
        except StopIteration:
            out.extend(list(bi))
            break
        try:
            out.append(next(bi))
        except StopIteration:
            out.extend(list(ai))
            break
    # Dedup while preserving order.
    seen: set[str] = set()
    deduped: list[str] = []
    for n in out:
        if n in seen:
            continue
        seen.add(n)
        deduped.append(n)
    return deduped


def forenames_for(country: str, gender: str) -> list[str]:
    """Return a non-empty list of forenames suited to country+gender.

    Falls back through: requested -> opposite-gender same country ->
    English-speaking fallback -> hard-coded safety list.
    """
    code = _country_code(country)
    gkey = _gender_key(gender)
    bucket = _FORENAMES_RAW.get(code, {})

    if gkey == "M" or gkey == "F":
        names = bucket.get(gkey) or []
        if names:
            return names
        # Fall back to the other gender in the same country before crossing borders.
        other = "F" if gkey == "M" else "M"
        names = bucket.get(other) or []
        if names:
            return names
    else:
        # NonBinary: blend male and female pools.
        m = bucket.get("M") or []
        f = bucket.get("F") or []
        blended = _interleave(m, f)
        if blended:
            return blended

    # Cross-country fallback.
    fb = _FORENAMES_RAW.get(_countries.DEFAULT_COUNTRY_CODE, {})
    if gkey in ("M", "F"):
        names = fb.get(gkey) or []
        if names:
            return names
    blended = _interleave(fb.get("M") or [], fb.get("F") or [])
    if blended:
        return blended

    # Final safety net.
    return _SAFETY_FORENAMES.get(gkey or "NB", _SAFETY_FORENAMES["NB"])


def surnames_for(country: str) -> list[str]:
    code = _country_code(country)
    names = _SURNAMES_RAW.get(code) or _SURNAMES_RAW.get(_countries.DEFAULT_COUNTRY_CODE) or []
    if names:
        return names
    return _SAFETY_SURNAMES


def random_forename(country: str, gender: str, rng) -> str:
    pool = forenames_for(country, gender)
    return rng.choice(pool)


def random_surname(country: str, rng) -> str:
    pool = surnames_for(country)
    return rng.choice(pool)


def random_full_name(country: str, gender: str, rng) -> tuple[str, str]:
    """Returns (first_name, last_name) — useful for NPC seeding."""
    return random_forename(country, gender, rng), random_surname(country, rng)


# --- Legacy compatibility -------------------------------------------------
# Older code (and the smoke tests) imports a flat NAMES[gender] -> list[str].
# Build it from the default-country pool so existing call sites keep working.

def _legacy_names() -> dict[str, list[str]]:
    default = _FORENAMES_RAW.get(_countries.DEFAULT_COUNTRY_CODE, {})
    return {
        "Male": default.get("M", _SAFETY_FORENAMES["M"]),
        "Female": default.get("F", _SAFETY_FORENAMES["F"]),
        "NonBinary": _interleave(default.get("M", []), default.get("F", [])) or _SAFETY_FORENAMES["NB"],
    }


# Final safety net so the module is usable even if _names_data is missing.
_SAFETY_FORENAMES = {
    "M": ["Oliver", "George", "Arthur", "Noah", "Muhammad", "Leo", "Oscar", "Harry", "Jack", "Henry"],
    "F": ["Olivia", "Amelia", "Isla", "Ava", "Ivy", "Freya", "Lily", "Florence", "Mia", "Willow"],
    "NB": ["Alex", "Jordan", "Charlie", "Sam", "Taylor", "Morgan", "Casey", "Riley", "Quinn", "Rowan"],
}
_SAFETY_SURNAMES = ["Smith", "Johnson", "Brown", "Taylor", "Wilson", "Davies", "Evans", "Thomas", "Roberts", "Walker"]

NAMES = _legacy_names()
