"""End-to-end persistence: a saved life must reload identically and continue
deterministically. Persistence bugs silently corrupt emotional continuity, so
this exercises the real controller path (not the core directly) and asserts
both state equivalence after load and identical deterministic continuation.
"""
from __future__ import annotations

from controller.game_controller import GameController


def _play(c: GameController, years: int) -> None:
    for _ in range(years):
        if c.state.mode != "PLAYING":
            return
        if c.state.pending_event_id is not None:
            c.choose(0)
            continue
        if c.state.career is None and c.state.character.age >= 18:
            c.apply_for_job("retail")
        c.age_up()


def test_save_load_roundtrip_and_deterministic_continuation(tmp_path):
    save_file = tmp_path / "life.json"

    a = GameController()
    a.new_game(seed=4242, name="", gender="Female", country="UK", talent="Academics")
    _play(a, 40)

    # Save, then rebuild a fresh controller from disk.
    a.save(save_file)
    b = GameController()
    b.load(save_file)

    # --- Equivalence immediately after load ---
    assert b.state.to_dict() == a.state.to_dict()
    assert b.state.character.age == a.state.character.age
    assert b.state.money == a.state.money
    assert b.state.tick == a.state.tick
    assert b.state.last_help_tick == a.state.last_help_tick
    assert [(r.npc_id, r.kind, r.relationship, r.alive) for r in b.state.relationships] \
        == [(r.npc_id, r.kind, r.relationship, r.alive) for r in a.state.relationships]
    assert (b.state.career is None) == (a.state.career is None)
    assert b.state.world.to_dict() == a.state.world.to_dict()

    # --- Identical deterministic continuation from equivalent states ---
    _play(a, 25)
    _play(b, 25)
    assert b.state.to_dict() == a.state.to_dict()
    assert [f.text for f in b.state.feed] == [f.text for f in a.state.feed]


def test_save_without_active_game_raises(tmp_path):
    """Saving before new_game() must fail loudly — silently writing nothing
    would let the UI think a save exists when it doesn't."""
    import pytest
    c = GameController()
    with pytest.raises(RuntimeError):
        c.save(tmp_path / "empty.json")


def test_load_missing_file_raises(tmp_path):
    import pytest
    c = GameController()
    with pytest.raises(FileNotFoundError):
        c.load(tmp_path / "does-not-exist.json")


def test_load_corrupt_json_raises_valueerror(tmp_path):
    import pytest
    bad = tmp_path / "broken.json"
    bad.write_text("{not valid json")
    c = GameController()
    with pytest.raises(ValueError):
        c.load(bad)


def test_load_non_object_json_root_raises_valueerror(tmp_path):
    """Valid JSON whose root isn't an object (e.g. `[]`, `"bad"`, `null`) must
    surface as ValueError, not AttributeError — otherwise the bridge envelope
    (which only catches OSError/ValueError) throws into JS instead of
    rendering a clean schema-mismatch toast."""
    import pytest
    c = GameController()
    for content in ("[]", '"bad"', "null", "42"):
        bad = tmp_path / "root.json"
        bad.write_text(content)
        with pytest.raises(ValueError):
            c.load(bad)


def test_save_is_atomic_no_partial_writes(tmp_path):
    """A successful save() leaves exactly the final file — no .tmp leftover."""
    save_file = tmp_path / "life.json"
    c = GameController()
    c.new_game(seed=1, name="", gender="Male", country="UK", talent="Sports")
    c.save(save_file)
    assert save_file.exists()
    assert not (tmp_path / "life.json.tmp").exists()


def test_load_missing_partner_and_weak_ties_survive_roundtrip(tmp_path):
    """A life that has formed a partner / weak ties must reload with them intact."""
    save_file = tmp_path / "life2.json"
    c = GameController()
    c.new_game(seed=7, name="", gender="Male", country="US", talent="Acting")
    _play(c, 60)  # long enough that weak ties / a partner are likely

    kinds_before = sorted(r.kind for r in c.state.relationships if r.alive)
    c.save(save_file)

    d = GameController()
    d.load(save_file)
    kinds_after = sorted(r.kind for r in d.state.relationships if r.alive)
    assert kinds_after == kinds_before
    assert [a.npc_id for a in d.state.agents] == [a.npc_id for a in c.state.agents]
