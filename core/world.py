"""World-level macro simulation (Phase 4A).

Keeps a tiny deterministic model (inflation, unemployment, recession/war flags)
that advances once per year from core.sim.age_up.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from typing import TYPE_CHECKING

from core.rng import Rng
if TYPE_CHECKING:
    from core.state import GameState

_MIN_INFLATION_INDEX = 0.5
_MAX_INFLATION_INDEX = 3.0


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


@dataclass
class World:
    year: int = 0
    inflation_index: float = 1.0
    unemployment_rate: float = 0.05
    recession: bool = False
    war: bool = False

    def clamped(self) -> "World":
        inf = self.inflation_index
        if not math.isfinite(inf):
            inf = 1.0
        unemp = self.unemployment_rate
        if not math.isfinite(unemp):
            unemp = 0.05
        return World(
            year=max(0, int(self.year)),
            inflation_index=_clamp(inf, _MIN_INFLATION_INDEX, _MAX_INFLATION_INDEX),
            unemployment_rate=_clamp(unemp, 0.0, 1.0),
            recession=bool(self.recession),
            war=bool(self.war),
        )

    def to_dict(self) -> dict:
        return {
            "year": self.year,
            "inflation_index": self.inflation_index,
            "unemployment_rate": self.unemployment_rate,
            "recession": self.recession,
            "war": self.war,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "World":
        return cls(
            year=data.get("year", 0),
            inflation_index=data.get("inflation_index", 1.0),
            unemployment_rate=data.get("unemployment_rate", 0.05),
            recession=data.get("recession", False),
            war=data.get("war", False),
        ).clamped()


def tick_world(state: GameState, rng: Rng) -> None:
    world = state.world.clamped()
    world.year = state.character.age if state.character else world.year + 1

    prev_recession = world.recession
    prev_inflation = world.inflation_index

    inflation_delta = rng.uniform(-0.015, 0.045)
    if world.recession:
        inflation_delta += rng.uniform(-0.02, 0.0)
    world.inflation_index = _clamp(world.inflation_index * (1.0 + inflation_delta), _MIN_INFLATION_INDEX, _MAX_INFLATION_INDEX)

    unemp_delta = rng.uniform(-0.012, 0.012)
    if world.recession:
        unemp_delta += rng.uniform(0.005, 0.02)
    world.unemployment_rate = _clamp(world.unemployment_rate + unemp_delta, 0.02, 0.25)

    recession_pressure = 0.0
    if world.inflation_index > 1.15:
        recession_pressure += 0.08
    if world.unemployment_rate > 0.09:
        recession_pressure += 0.18

    if world.recession:
        recover_chance = 0.15 + max(0.0, 0.10 - world.unemployment_rate)
        if rng.chance(recover_chance):
            world.recession = False
    else:
        trigger_chance = min(0.35, 0.05 + recession_pressure)
        if rng.chance(trigger_chance):
            world.recession = True

    state.world = world.clamped()

    if prev_recession != state.world.recession:
        cid = f"world:recession:{state.tick}"
        state.causal_chain.append({
            "id": cid,
            "kind": "world_recession_start" if state.world.recession else "world_recession_end",
            "tick": state.tick,
        })
        msg = "A recession begins and the economy tightens." if state.world.recession else "The recession ends and recovery begins."
        from core.state import FeedEntry
        state.feed.append(FeedEntry(age=state.character.age if state.character else 0, text=msg, kind="bad" if state.world.recession else "good", cause_id=cid, entry_id=f"feed:world:recession:{state.tick}"))

    if (state.world.inflation_index - prev_inflation) >= 0.08:
        cid = f"world:inflation_spike:{state.tick}"
        state.causal_chain.append({
            "id": cid,
            "kind": "world_inflation_spike",
            "tick": state.tick,
        })
        from core.state import FeedEntry
        state.feed.append(FeedEntry(age=state.character.age if state.character else 0, text="Prices jump sharply this year as inflation accelerates.", kind="bad", cause_id=cid, entry_id=f"feed:world:inflation:{state.tick}"))
