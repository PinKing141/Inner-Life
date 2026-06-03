"""Settings v1 — dataclass, persistence, controller verb, snapshot
field, tolerance to corrupt/legacy on-disk state.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from controller import settings as settings_io
from controller.game_controller import GameController
from core.settings import FONT_SIZES, Settings


@pytest.fixture(autouse=True)
def _isolated_settings_path(tmp_path, monkeypatch):
    """Redirect SETTINGS_PATH to a tmp file per test so the developer's
    real ~/.inner-life-settings.json is never touched and tests can't
    leak state into each other."""
    monkeypatch.setattr(settings_io, "SETTINGS_PATH",
                        tmp_path / "settings.json")
    yield


# --- Dataclass invariants ------------------------------------------------


def test_default_settings_are_safe_for_first_run():
    s = Settings()
    assert s.font_size == "medium"
    assert s.reduced_motion is False
    assert s.high_contrast is False
    assert s.confirm_risky_actions is True  # default ON — guards against accidental destructive taps
    assert s.show_stat_deltas is False


def test_from_dict_drops_unknown_keys_and_fills_missing():
    """Forward + backward compat: old settings files lacking new keys
    must load fine, and futuristic keys we don't recognise must not
    blow up the dataclass."""
    s = Settings.from_dict({
        "font_size": "large",
        "exoplanet_density": 0.5,   # unknown — must be ignored
    })
    assert s.font_size == "large"
    assert s.reduced_motion is False  # default kept


def test_from_dict_rejects_bad_font_size_token():
    """A hand-edited settings file with a typo'd font_size shouldn't
    leak that token into the snapshot — it would make CSS attribute
    selectors miss and the UI would render at default anyway."""
    s = Settings.from_dict({"font_size": "humungous"})
    assert s.font_size == "medium"


def test_from_dict_handles_none_gracefully():
    assert Settings.from_dict(None).font_size == "medium"


# --- update() validation ------------------------------------------------


@pytest.mark.parametrize("size", FONT_SIZES)
def test_update_font_size_accepts_valid_tokens(size):
    s = Settings()
    assert s.update("font_size", size) is True
    assert s.font_size == size


def test_update_font_size_refuses_invalid_token():
    s = Settings()
    assert s.update("font_size", "humungous") is False
    assert s.font_size == "medium"  # untouched


def test_update_refuses_unknown_key():
    s = Settings()
    assert s.update("imaginary_setting", True) is False


@pytest.mark.parametrize("key", [
    "reduced_motion", "high_contrast",
    "confirm_risky_actions", "show_stat_deltas",
])
def test_update_bool_field_accepts_python_bool(key):
    s = Settings()
    starting = getattr(s, key)
    assert s.update(key, not starting) is True
    assert getattr(s, key) == (not starting)


@pytest.mark.parametrize("text,expected", [
    ("true", True), ("True", True), ("TRUE", True),
    ("false", False), ("False", False), ("FALSE", False),
])
def test_update_bool_field_parses_js_string_token(text, expected):
    """The bridge slot is typed `(str, str)` so JS sends 'true'/'false'.
    The dataclass parses these so the controller doesn't have to."""
    s = Settings()
    s.reduced_motion = not expected
    assert s.update("reduced_motion", text) is True
    assert s.reduced_motion is expected


def test_update_bool_field_refuses_random_string():
    s = Settings()
    s.reduced_motion = False
    assert s.update("reduced_motion", "yes please") is False
    assert s.reduced_motion is False  # untouched


# --- Persistence --------------------------------------------------------


def test_load_returns_defaults_when_no_settings_file_exists():
    assert not settings_io.SETTINGS_PATH.exists()
    loaded = settings_io.load()
    assert loaded.font_size == "medium"


def test_load_returns_defaults_on_corrupt_json():
    settings_io.SETTINGS_PATH.write_text("not valid json {", encoding="utf-8")
    loaded = settings_io.load()
    assert loaded.font_size == "medium"
    assert loaded.reduced_motion is False


def test_save_then_load_round_trips():
    s = Settings(font_size="large", reduced_motion=True,
                 confirm_risky_actions=False)
    assert settings_io.save(s) is True
    loaded = settings_io.load()
    assert loaded.font_size == "large"
    assert loaded.reduced_motion is True
    assert loaded.confirm_risky_actions is False


def test_save_is_atomic_via_temp_file():
    """Same pattern as save_slots — the temp file must not linger after
    a successful save, so a partial write never appears on disk."""
    settings_io.save(Settings())
    tmp = settings_io.SETTINGS_PATH.with_suffix(".json.tmp")
    assert not tmp.exists()


# --- Controller integration --------------------------------------------


def test_controller_loads_settings_on_init():
    """Pre-seed disk, instantiate the controller, prove it picked up."""
    settings_io.save(Settings(font_size="small", high_contrast=True))
    c = GameController()
    assert c.settings.font_size == "small"
    assert c.settings.high_contrast is True


def test_controller_set_setting_persists_to_disk():
    c = GameController()
    snap = c.set_setting("font_size", "large")
    assert snap["settings"]["font_size"] == "large"
    # Reload from disk and confirm the change stuck.
    assert settings_io.load().font_size == "large"


def test_controller_set_setting_refuses_unknown_key_silently():
    c = GameController()
    snap = c.set_setting("imaginary", "blue")
    # Returned snapshot reflects unchanged settings.
    assert snap["settings"]["font_size"] == "medium"


def test_controller_set_setting_refuses_bad_font_size():
    c = GameController()
    c.set_setting("font_size", "humungous")
    assert c.settings.font_size == "medium"


# --- Snapshot --------------------------------------------------------


def test_snapshot_in_creation_mode_includes_settings():
    """The character creation screen needs font size + motion before
    any GameState exists. The CREATION-mode short-circuit must still
    expose settings."""
    c = GameController()
    snap = c.snapshot()
    assert snap["mode"] == "CREATION"
    assert "settings" in snap
    assert snap["settings"]["font_size"] == "medium"


def test_snapshot_in_playing_mode_includes_settings():
    c = GameController()
    c.new_game(seed=1, name="", gender="Female", country="US", talent="Sports")
    snap = c.snapshot()
    assert snap["mode"] == "PLAYING"
    assert "settings" in snap


# --- New game doesn't reset settings ----------------------------------


def test_new_game_does_not_reset_user_settings():
    """Settings are user-level, not life-level. Starting a fresh game
    must not wipe accessibility preferences."""
    c = GameController()
    c.set_setting("font_size", "large")
    c.set_setting("reduced_motion", "true")
    c.new_game(seed=99, name="", gender="Male", country="US", talent="Sports")
    snap = c.snapshot()
    assert snap["settings"]["font_size"] == "large"
    assert snap["settings"]["reduced_motion"] is True


def test_loading_a_save_does_not_reset_user_settings():
    """Same contract on load: pulling a saved character must not
    change the player's accessibility prefs."""
    c = GameController()
    c.new_game(seed=1, name="", gender="Female", country="US", talent="Sports")
    # Save with default settings.
    c.set_setting("font_size", "small")
    # Force-save via the legacy path API.
    c.save(Path(settings_io.SETTINGS_PATH).parent / "_one_off_save.json")
    # Switch settings, then reload the save — settings should stick.
    c.set_setting("font_size", "large")
    c.load(Path(settings_io.SETTINGS_PATH).parent / "_one_off_save.json")
    assert c.settings.font_size == "large"
