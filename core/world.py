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

ERA_PROFILES: dict[str, dict[str, float]] = {
    "postwar": {
        "inflation_bias": 0.006,
        "unemployment_bias": -0.004,
        "recession_trigger_shift": -0.01,
        "recovery_bonus": 0.04,
    },
    "boom": {
        "inflation_bias": 0.010,
        "unemployment_bias": -0.006,
        "recession_trigger_shift": -0.02,
        "recovery_bonus": 0.05,
    },
    "stagflation": {
        "inflation_bias": 0.020,
        "unemployment_bias": 0.006,
        "recession_trigger_shift": 0.04,
        "recovery_bonus": -0.04,
    },
}


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


@dataclass
class World:
    year: int = 0
    inflation_index: float = 1.0
    unemployment_rate: float = 0.05
    recession: bool = False
    war: bool = False
    era_regime: str = "postwar"

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
            era_regime=self.era_regime if self.era_regime in ERA_PROFILES else "postwar",
        )

    def to_dict(self) -> dict:
        return {
            "year": self.year,
            "inflation_index": self.inflation_index,
            "unemployment_rate": self.unemployment_rate,
            "recession": self.recession,
            "war": self.war,
            "era_regime": self.era_regime,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "World":
        return cls(
            year=data.get("year", 0),
            inflation_index=data.get("inflation_index", 1.0),
            unemployment_rate=data.get("unemployment_rate", 0.05),
            recession=data.get("recession", False),
            war=data.get("war", False),
            era_regime=data.get("era_regime", "postwar"),
        ).clamped()


def tick_world(state: GameState, rng: Rng) -> None:
    world = state.world.clamped()
    world.year = state.character.age if state.character else world.year + 1

    prev_recession = world.recession
    prev_inflation = world.inflation_index
    prev_era = world.era_regime

    prev_war = world.war
    profile = ERA_PROFILES.get(world.era_regime, ERA_PROFILES["postwar"])

    if rng.chance(0.08):
        names = list(ERA_PROFILES.keys())
        world.era_regime = names[rng.randint(0, len(names) - 1)]
        profile = ERA_PROFILES[world.era_regime]

    inflation_delta = rng.uniform(-0.015, 0.045) + profile["inflation_bias"]
    if world.recession:
        inflation_delta += rng.uniform(-0.02, 0.0)
    world.inflation_index = _clamp(world.inflation_index * (1.0 + inflation_delta), _MIN_INFLATION_INDEX, _MAX_INFLATION_INDEX)

    unemp_delta = rng.uniform(-0.012, 0.012) + profile["unemployment_bias"]
    if world.recession:
        unemp_delta += rng.uniform(0.005, 0.02)
    world.unemployment_rate = _clamp(world.unemployment_rate + unemp_delta, 0.02, 0.25)

    recession_pressure = 0.0
    if world.inflation_index > 1.15:
        recession_pressure += 0.08
    if world.unemployment_rate > 0.09:
        recession_pressure += 0.18

    if world.recession:
        recover_chance = 0.15 + max(0.0, 0.10 - world.unemployment_rate) + profile["recovery_bonus"]
        if rng.chance(recover_chance):
            world.recession = False
    else:
        trigger_chance = min(0.35, max(0.01, 0.05 + recession_pressure + profile["recession_trigger_shift"]))
        if rng.chance(trigger_chance):
            world.recession = True

    if world.war:
        if rng.chance(0.12):
            world.war = False
    else:
        if rng.chance(0.05 if world.recession else 0.02):
            world.war = True

    state.world = world.clamped()

    from core.causal import append_cause

    if prev_era != state.world.era_regime:
        cid = f"world:era_shift:{state.tick}"
        append_cause(
            state,
            node_id=cid,
            kind="world_era_shift",
            source="world.tick_world",
            details={"from": prev_era, "to": state.world.era_regime},
        )
        from core.state import FeedEntry
        state.feed.append(FeedEntry(age=state.character.age if state.character else 0, text=f"Global mood shifts from {prev_era} to {state.world.era_regime}.", kind="neutral", cause_id=cid, entry_id=f"feed:world:era:{state.tick}"))

    if prev_war != state.world.war:
        cid = f"world:war:{state.tick}"
        append_cause(
            state,
            node_id=cid,
            kind="world_war_start" if state.world.war else "world_war_end",
            source="world.tick_world",
            details={"era_regime": state.world.era_regime},
        )
        from core.state import FeedEntry
        text = "A regional war breaks out abroad; analysts warn of global ripple effects." if state.world.war else "A major regional conflict cools and markets stabilize slightly."
        state.feed.append(FeedEntry(age=state.character.age if state.character else 0, text=text, kind="neutral", cause_id=cid, entry_id=f"feed:world:war:{state.tick}"))

    if prev_recession != state.world.recession:
        cid = f"world:recession:{state.tick}"
        append_cause(
            state,
            node_id=cid,
            kind="world_recession_start" if state.world.recession else "world_recession_end",
            source="world.tick_world",
            details={"unemployment_rate": state.world.unemployment_rate, "inflation_index": state.world.inflation_index, "era_regime": state.world.era_regime},
        )
        msg = "A recession begins and the economy tightens." if state.world.recession else "The recession ends and recovery begins."
        from core.state import FeedEntry
        state.feed.append(FeedEntry(age=state.character.age if state.character else 0, text=msg, kind="bad" if state.world.recession else "good", cause_id=cid, entry_id=f"feed:world:recession:{state.tick}"))

    if (state.world.inflation_index - prev_inflation) >= 0.08:
        cid = f"world:inflation_spike:{state.tick}"
        append_cause(state, node_id=cid, kind="world_inflation_spike", source="world.tick_world", details={"inflation_index": state.world.inflation_index})
        from core.state import FeedEntry
        state.feed.append(FeedEntry(age=state.character.age if state.character else 0, text="Prices jump sharply this year as inflation accelerates.", kind="bad", cause_id=cid, entry_id=f"feed:world:inflation:{state.tick}"))
