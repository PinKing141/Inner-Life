"""Save slots — multiple persistent saves, slot metadata peek, round-trip.

Covers the slot path resolution, list_slots peek behaviour (incl.
graceful degradation on corrupt files), save/load round-trip with the
``_slot_meta`` shim, delete behaviour, range validation, and the
controller verbs that wrap the storage layer.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from controller import save_slots
from controller.game_controller import GameController


@pytest.fixture(autouse=True)
def _isolated_save_dir(tmp_path, monkeypatch):
    """Redirect SAVE_DIR to a tmp dir per test so the developer's real
    ~/.inner-life-saves is never touched, and tests can't interfere with
    each other."""
    monkeypatch.setattr(save_slots, "SAVE_DIR", tmp_path / "saves")
    yield


def _new_controller(seed: int = 1, age: int = 25):
    c = GameController()
    c.new_game(seed=seed, name="", gender="Female", country="US", talent="Sports")
    c.state.character.age = age
    return c


# --- Path / list_slots --------------------------------------------------


def test_slot_path_resolves_to_saves_dir():
    assert save_slots.slot_path(1).name == "slot_1.json"
    assert save_slots.slot_path(5).name == "slot_5.json"


def test_list_slots_returns_all_slots_with_exists_false_when_empty():
    rows = save_slots.list_slots()
    assert len(rows) == save_slots.SLOT_COUNT
    for r in rows:
        assert r["exists"] is False
        assert r["character_name"] == ""


def test_list_slots_picks_up_an_existing_save():
    c = _new_controller()
    c.save_to_slot(2)
    rows = save_slots.list_slots()
    slot2 = next(r for r in rows if r["slot_id"] == 2)
    assert slot2["exists"] is True
    assert slot2["character_name"] == c.state.character.name
    assert slot2["age"] == 25
    # Other slots stay empty.
    for r in rows:
        if r["slot_id"] != 2:
            assert r["exists"] is False


def test_list_slots_survives_a_corrupt_save_file():
    """If a slot file is unreadable JSON, list_slots must report the
    slot as empty rather than crash the picker menu."""
    save_slots.SAVE_DIR.mkdir(parents=True, exist_ok=True)
    save_slots.slot_path(3).write_text("not valid json {", encoding="utf-8")
    rows = save_slots.list_slots()
    assert rows[2]["exists"] is False


# --- Range validation --------------------------------------------------


@pytest.mark.parametrize("bad_id", [0, -1, save_slots.SLOT_COUNT + 1, 999])
def test_save_load_delete_refuse_out_of_range_slot_ids(bad_id):
    state_dict = {"character": {"name": "X"}, "tick": 0}
    with pytest.raises(ValueError):
        save_slots.save_to_slot(bad_id, state_dict)
    with pytest.raises(ValueError):
        save_slots.load_from_slot(bad_id)
    with pytest.raises(ValueError):
        save_slots.delete_slot(bad_id)


# --- Round-trip --------------------------------------------------------


def test_save_then_load_round_trips_state():
    c = _new_controller()
    age_before = c.state.character.age
    money_before = c.state.money = 12_345
    c.save_to_slot(1)

    # Mutate the live state, then load — slot contents must overwrite.
    c.state.character.age = 99
    c.state.money = 999

    c.load_from_slot(1)
    assert c.state.character.age == age_before
    assert c.state.money == money_before


def test_save_strips_slot_meta_on_load_so_from_dict_isnt_polluted():
    """``GameState.from_dict`` doesn't know about _slot_meta. The
    save_slots layer must remove it before passing data through."""
    c = _new_controller()
    c.save_to_slot(1)
    on_disk = json.loads(save_slots.slot_path(1).read_text())
    assert "_slot_meta" in on_disk  # meta is written
    cleaned = save_slots.load_from_slot(1)
    assert "_slot_meta" not in cleaned  # but stripped before GameState sees it


def test_save_to_slot_is_atomic_via_temp_file():
    """The temp-file + rename pattern means the .json never appears
    half-written. We can't easily simulate a crash; just verify the
    temp file is gone after a successful save."""
    c = _new_controller()
    c.save_to_slot(1)
    tmp = save_slots.slot_path(1).with_suffix(".json.tmp")
    assert not tmp.exists()


# --- Delete -------------------------------------------------------------


def test_delete_slot_removes_the_file():
    c = _new_controller()
    c.save_to_slot(1)
    assert save_slots.slot_path(1).exists()
    assert save_slots.delete_slot(1) is True
    assert not save_slots.slot_path(1).exists()


def test_delete_empty_slot_is_noop():
    """Already-empty slots can be 'deleted' without error so the UI
    delete button doesn't fail on double-tap or stale state."""
    assert save_slots.delete_slot(4) is True


# --- Legacy load (single-file path) coexistence ------------------------


def test_legacy_load_strips_slot_meta_so_slot_files_are_path_loadable():
    """`controller.load(path)` is the back-compat single-file path. If
    the user points it at a slot file directly (e.g., file-picker UI),
    the embedded `_slot_meta` must be stripped before from_dict sees it."""
    c = _new_controller()
    c.save_to_slot(2)
    # Force-load via the legacy path API using the slot file directly.
    c.state.character.age = 999
    c.load(save_slots.slot_path(2))
    assert c.state.character.age == 25


# --- Controller verbs --------------------------------------------------


def test_controller_list_save_slots_returns_count_rows():
    c = _new_controller()
    rows = c.list_save_slots()
    assert len(rows) == save_slots.SLOT_COUNT


def test_controller_load_from_empty_slot_raises_filenotfound():
    c = _new_controller()
    with pytest.raises(FileNotFoundError):
        c.load_from_slot(3)


def test_controller_delete_save_slot_returns_true():
    c = _new_controller()
    c.save_to_slot(5)
    assert c.delete_save_slot(5) is True
    rows = c.list_save_slots()
    slot5 = next(r for r in rows if r["slot_id"] == 5)
    assert slot5["exists"] is False


# --- Meta peek details -------------------------------------------------


def test_slot_meta_records_money_and_country():
    """Meta has to include enough fields for the UI to render slot rows
    without re-reading the whole save."""
    c = _new_controller()
    c.state.money = 77_777
    c.save_to_slot(1)
    rows = save_slots.list_slots()
    assert rows[0]["money"] == 77_777
    assert rows[0]["country"] == "United States"


def test_meta_falls_back_when_slot_lacks_slot_meta_key():
    """Pre-slot-era saves dropped into the slots directory would lack
    `_slot_meta`. list_slots derives a minimal peek from the character
    block so they still appear in the picker."""
    save_slots.SAVE_DIR.mkdir(parents=True, exist_ok=True)
    save_slots.slot_path(1).write_text(json.dumps({
        "character": {"name": "Legacy", "age": 42, "country": "France"},
        "tick": 42,
        "money": 100,
    }), encoding="utf-8")
    rows = save_slots.list_slots()
    assert rows[0]["exists"] is True
    assert rows[0]["character_name"] == "Legacy"
    assert rows[0]["age"] == 42


# --- Round-trip across all the slice features --------------------------


def test_slot_save_load_preserves_recent_phase_features():
    """End-to-end smoke that the slot save format captures everything
    the recent slices added (pregnancy, dating, crime record,
    vehicles, milestones) — guards against a forgotten field rebuild
    blowing up next time we add a phase."""
    c = _new_controller()
    # Touch every recent state field at least once.
    c.state.money = 50_000
    c.state.dating = {"npc_id": 42, "name": "Mx Test", "age": 24,
                      "gender": "NonBinary", "chemistry": 55,
                      "dates_been_on": 2, "started_tick": c.state.tick}
    c.state.crime.past_offences = ["Pickpocketing"]
    c.state.milestones_seen = [18, 30]
    c.state.vehicles.append({
        "instance_id": 1, "car_id": "used_hatchback", "name": "X",
        "brand": "Ford", "model": "Fiesta",
        "purchase_price": 3000, "current_value": 2500,
        "age_years": 1, "depreciation_rate": 0.08,
    })
    c.save_to_slot(1)
    # Wipe live state and reload.
    c.state.money = 0
    c.state.dating = None
    c.state.crime.past_offences = []
    c.state.milestones_seen = []
    c.state.vehicles = []
    c.load_from_slot(1)
    assert c.state.money == 50_000
    assert c.state.dating is not None
    assert c.state.dating["chemistry"] == 55
    assert c.state.crime.past_offences == ["Pickpocketing"]
    assert c.state.milestones_seen == [18, 30]
    assert len(c.state.vehicles) == 1
    assert c.state.vehicles[0]["brand"] == "Ford"
