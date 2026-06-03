"""Settings persistence — load/save the user-level settings file.

Mirrors the controller/save_slots.py pattern: stateless module that
the GameController calls into. Settings live at
``~/.inner-life-settings.json`` — separate from the saves directory
because they're a property of the user, not a particular life.

Tolerance is the design goal: missing file → defaults, corrupt JSON
→ defaults (with a log line eventually), unknown keys ignored. This
keeps a forward-incompatible settings file from bricking the app.
"""
from __future__ import annotations

import json
from pathlib import Path

from core.settings import Settings


SETTINGS_PATH = Path.home() / ".inner-life-settings.json"


def load() -> Settings:
    """Read the on-disk settings, falling back to defaults on any
    error. Never raises — the caller (controller init) shouldn't have
    to wrap a try/except just to read user preferences."""
    if not SETTINGS_PATH.exists():
        return Settings()
    try:
        raw = SETTINGS_PATH.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return Settings()
    return Settings.from_dict(data)


def save(settings: Settings) -> bool:
    """Persist settings atomically via temp-file + rename. Returns True
    on success, False on any I/O failure. Same pattern as save_slots
    so a crash mid-write can never leave a half-corrupt settings file."""
    try:
        payload = json.dumps(settings.to_dict(), indent=2)
        tmp = SETTINGS_PATH.with_suffix(SETTINGS_PATH.suffix + ".tmp")
        tmp.write_text(payload, encoding="utf-8")
        tmp.replace(SETTINGS_PATH)
        return True
    except OSError:
        return False
