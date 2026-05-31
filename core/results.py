"""Typed result records for player-facing verbs.

These replace the bare tuples that economy / housing / relationships used to
return. They are ``NamedTuple`` subclasses, so they stay tuple-compatible —
``ok, msg = apply_for_job(...)`` and ``result[0]`` both keep working — while
adding named, typed fields (``result.ok``, ``result.message``) that read
clearly at the call site and let mypy check shapes.
"""
from __future__ import annotations

from typing import NamedTuple


class ActionResult(NamedTuple):
    """Outcome of a player verb that either happens or doesn't, with a line of
    feed text. State is mutated by the verb only when ``ok`` is True."""
    ok: bool
    message: str


class PromotionResult(NamedTuple):
    """Like ActionResult but carries the promotion payload the UI raises as a
    popup. ``promotion`` is None on refusal."""
    ok: bool
    message: str
    promotion: dict | None = None


class Cashflow(NamedTuple):
    """A year's budget projection. Pure — annual_cashflow never mutates state;
    the caller applies ``earnings - living_cost`` to the balance."""
    earnings: int
    living_cost: int
    note: str
