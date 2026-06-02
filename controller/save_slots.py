"""Save slot management — N named slots instead of a single save file.

Before this module, the game had exactly one persistent save at
``~/.inner-life-save.json``. That bridge surface is still present for
back-compat; this module adds a parallel directory with numbered slots
so the player can keep multiple lives in flight (try a doctor career,
keep a heir run, save before a risky crime attempt).

Storage layout
--------------

::

    ~/.inner-life-saves/
        slot_1.json
        slot_2.json
        ...
        slot_5.json

Each slot file is a full GameState ``to_dict()`` payload, with one
synthetic key:

    "_slot_meta": {
        "character_name": "Lin Ward",
        "age": 34,
        "country": "United States",
        "tick": 34,
        "saved_at": "2026-06-02T14:01:32",
        "money": 12_345,
    }

The meta dict is written at save time so ``list_slots`` can peek a
slot's contents without deserialising the whole GameState (fast UI
refresh on the slot picker). On load, ``_slot_meta`` is stripped from
the dict before ``GameState.from_dict`` sees it.

Determinism / atomicity
-----------------------

Writes go through a temp file + rename (same pattern as the legacy
single-file save) so a crash mid-write never corrupts a slot.

Number of slots
---------------

Five slots is a v1 sensible default; ``SLOT_COUNT`` is the single
source of truth — change here, UI picks it up via ``list_slots`` and
shows the right number of rows.
"""
from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any


SLOT_COUNT = 5
SAVE_DIR = Path.home() / ".inner-life-saves"


def slot_path(slot_id: int) -> Path:
    """Resolve the on-disk path for a slot id. Doesn't create the dir."""
    return SAVE_DIR / f"slot_{slot_id}.json"


def _peek_meta(path: Path) -> dict | None:
    """Read just enough of a slot file to populate the picker UI.
    Returns None on any read error so a corrupt slot degrades to
    "Empty" instead of crashing the menu.
    """
    if not path.exists():
        return None
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return None
    meta = data.get("_slot_meta")
    if isinstance(meta, dict):
        return meta
    # Older save without _slot_meta — derive a minimal peek from the
    # character block. Keeps backward compat with whatever the user
    # might have already lying around.
    char = data.get("character") or {}
    return {
        "character_name": char.get("name", "Unknown"),
        "age": char.get("age", 0),
        "country": char.get("country", ""),
        "tick": data.get("tick", 0),
        "saved_at": "",
        "money": data.get("money", 0),
    }


def list_slots() -> list[dict]:
    """Return ``SLOT_COUNT`` rows, one per slot, with ``exists`` flag +
    metadata for the UI. Slots are 1-indexed for player-facing clarity.
    """
    rows: list[dict] = []
    for slot_id in range(1, SLOT_COUNT + 1):
        meta = _peek_meta(slot_path(slot_id))
        if meta is None:
            rows.append({
                "slot_id": slot_id,
                "exists": False,
                "character_name": "",
                "age": 0,
                "country": "",
                "tick": 0,
                "saved_at": "",
                "money": 0,
            })
        else:
            rows.append({
                "slot_id": slot_id,
                "exists": True,
                "character_name": meta.get("character_name", "Unknown"),
                "age": meta.get("age", 0),
                "country": meta.get("country", ""),
                "tick": meta.get("tick", 0),
                "saved_at": meta.get("saved_at", ""),
                "money": meta.get("money", 0),
            })
    return rows


def _build_meta(state_dict: dict[str, Any]) -> dict:
    char = state_dict.get("character") or {}
    return {
        "character_name": char.get("name", "Unknown"),
        "age": char.get("age", 0),
        "country": char.get("country", ""),
        "tick": state_dict.get("tick", 0),
        "saved_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "money": state_dict.get("money", 0),
    }


def save_to_slot(slot_id: int, state_dict: dict[str, Any]) -> None:
    """Write ``state_dict`` to the given slot. Adds ``_slot_meta``
    inline so future peeks are fast. Atomic via temp-file rename.

    Raises ``ValueError`` if ``slot_id`` is outside ``1..SLOT_COUNT`` —
    the bridge translates this to a user-visible error.
    """
    if not (1 <= slot_id <= SLOT_COUNT):
        raise ValueError(f"slot_id {slot_id} out of range (1..{SLOT_COUNT})")
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    payload = dict(state_dict)
    payload["_slot_meta"] = _build_meta(state_dict)
    path = slot_path(slot_id)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    tmp.replace(path)


def load_from_slot(slot_id: int) -> dict[str, Any]:
    """Read a slot and return the cleaned state dict (``_slot_meta``
    stripped so ``GameState.from_dict`` doesn't see it).

    Raises ``ValueError`` if ``slot_id`` is out of range or the slot is
    empty, ``OSError`` on read failure, and ``json.JSONDecodeError`` on
    parse failure (callers translate).
    """
    if not (1 <= slot_id <= SLOT_COUNT):
        raise ValueError(f"slot_id {slot_id} out of range (1..{SLOT_COUNT})")
    path = slot_path(slot_id)
    if not path.exists():
        raise FileNotFoundError(f"slot {slot_id} is empty")
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    data.pop("_slot_meta", None)
    return data


def delete_slot(slot_id: int) -> bool:
    """Remove a slot's save file. Returns True on success (or if the
    slot was already empty), False on filesystem error."""
    if not (1 <= slot_id <= SLOT_COUNT):
        raise ValueError(f"slot_id {slot_id} out of range (1..{SLOT_COUNT})")
    path = slot_path(slot_id)
    try:
        path.unlink(missing_ok=True)
        return True
    except OSError:
        return False
