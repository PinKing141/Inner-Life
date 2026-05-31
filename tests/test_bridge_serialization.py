"""Bridge JSON serialization — the `_json_default` safety net.

The snapshot tree keeps growing (predicates, enums, result records), and any
object that slips into it must NOT take down the whole UI. `_json_default` is
the best-effort fallback json.dumps reaches for on otherwise-unserializable
values; these tests pin down each branch so a regression there can't silently
blank the frontend.
"""
from __future__ import annotations

import dataclasses
import json
from enum import Enum

from bridge.web_bridge import _dumps, _json_default


@dataclasses.dataclass
class _Point:
    x: int
    y: int


class _Color(Enum):
    RED = "red"
    BLUE = "blue"


class _WithToDict:
    def to_dict(self) -> dict:
        return {"kind": "custom", "n": 1}


class _ToDictRaises:
    def to_dict(self):
        raise RuntimeError("boom")


class _Opaque:
    def __repr__(self) -> str:
        return "<opaque object>"


def test_dataclass_unwraps_to_dict():
    assert _json_default(_Point(1, 2)) == {"x": 1, "y": 2}


def test_enum_unwraps_to_value():
    assert _json_default(_Color.RED) == "red"


def test_set_and_frozenset_become_lists():
    assert sorted(_json_default({3, 1, 2})) == [1, 2, 3]
    assert sorted(_json_default(frozenset({"a", "b"}))) == ["a", "b"]


def test_object_with_to_dict_is_used():
    assert _json_default(_WithToDict()) == {"kind": "custom", "n": 1}


def test_failing_to_dict_degrades_to_type_repr():
    out = _json_default(_ToDictRaises())
    assert out["__type__"] == "_ToDictRaises"
    assert "repr" in out


def test_unknown_object_degrades_to_type_repr():
    out = _json_default(_Opaque())
    assert out == {"__type__": "_Opaque", "repr": "<opaque object>"}


def test_dumps_handles_mixed_nested_tree():
    payload = {
        "point": _Point(4, 5),
        "color": _Color.BLUE,
        "tags": {"x", "y"},
        "custom": _WithToDict(),
        "plain": [1, "two", 3.0, True, None],
    }
    decoded = json.loads(_dumps(payload))
    assert decoded["point"] == {"x": 4, "y": 5}
    assert decoded["color"] == "blue"
    assert sorted(decoded["tags"]) == ["x", "y"]
    assert decoded["custom"] == {"kind": "custom", "n": 1}
    assert decoded["plain"] == [1, "two", 3.0, True, None]


def test_dumps_returns_parseable_json_for_opaque_value():
    # A single opaque object at the root still produces valid JSON rather
    # than throwing — the whole point of the safety net.
    decoded = json.loads(_dumps(_Opaque()))
    assert decoded["__type__"] == "_Opaque"
