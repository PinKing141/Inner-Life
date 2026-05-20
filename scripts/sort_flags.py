#!/usr/bin/env python3
"""Sort flag SVGs into continent folders using restcountries for lookup.

Place this in the repository root and run from the project directory.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Optional

try:
    from urllib.request import urlopen
    from urllib.error import HTTPError, URLError
except Exception:
    raise


ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "ui" / "flags-svg" / "other"
OUT_BASE = ROOT / "ui" / "flags-svg"

CONTINENT_DIRS = {
    "Africa": OUT_BASE / "africa",
    "Asia": OUT_BASE / "asia",
    "Europe": OUT_BASE / "europe",
    "Oceania": OUT_BASE / "oceania",
    "Antarctic": OUT_BASE / "antarctic",
    "Americas": OUT_BASE / "americas",
    "North America": OUT_BASE / "north-america",
    "South America": OUT_BASE / "south-america",
    "Other": OUT_BASE / "other",
}


def ensure_dirs():
    for d in CONTINENT_DIRS.values():
        d.mkdir(parents=True, exist_ok=True)


def lookup_continent(alpha2: str) -> Optional[str]:
    # Use restcountries API to get region/subregion. Alpha2 must be 2 letters.
    url = f"https://restcountries.com/v3.1/alpha/{alpha2}"
    try:
        with urlopen(url, timeout=10) as resp:
            data = json.load(resp)
    except (HTTPError, URLError, TimeoutError):
        return None
    except Exception:
        return None

    # API returns a list for this endpoint
    if isinstance(data, list) and data:
        entry = data[0]
    elif isinstance(data, dict):
        entry = data
    else:
        return None

    region = entry.get("region")
    subregion = entry.get("subregion")
    if region == "Americas":
        if subregion and "South" in subregion:
            return "South America"
        return "North America"
    if region:
        return region
    return None


def classify(filename: str) -> str:
    code = filename.rsplit(".", 1)[0]
    # Some files use lowercase codes and some use region suffixes (eg gb-eng)
    code_up = code.upper()
    base = code_up.split("-")[0]
    # Special-cases and known mappings
    special = {
        "EU": "Europe",
        "XK": "Europe",
        "GBENG": "Europe",
        "GBNIR": "Europe",
        "GBSCT": "Europe",
        "GBWLS": "Europe",
    }
    if code_up in special:
        return special[code_up]
    continent = lookup_continent(base)
    if continent:
        return continent
    return "Other"


def main():
    if not SRC_DIR.exists():
        print("Source directory does not exist:", SRC_DIR)
        sys.exit(1)
    ensure_dirs()

    moved = []
    unmapped = []

    for p in sorted(SRC_DIR.glob("*.svg")):
        dest_continent = classify(p.name)
        if dest_continent == "Other":
            unmapped.append(p.name)
        dest_dir = CONTINENT_DIRS.get(dest_continent, CONTINENT_DIRS["Other"])
        dest = dest_dir / p.name
        try:
            shutil.move(str(p), str(dest))
            moved.append((p.name, dest_continent))
        except Exception as e:
            print("Failed to move", p, "->", dest, e)

    print("Moved files: {}".format(len(moved)))
    for name, cont in moved:
        print(f"  {name} -> {cont}")

    if unmapped:
        print("\nUnmapped files (left in 'other' folder): {}".format(len(unmapped)))
        for u in unmapped:
            print("  "+u)


if __name__ == "__main__":
    main()
