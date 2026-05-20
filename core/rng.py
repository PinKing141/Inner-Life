"""Deterministic RNG.

All randomness in the simulation must go through this module so that a given
seed produces a reproducible run. Never use the global `random` module in
core/ — that breaks determinism and makes Phase 7-style tracing harder.
"""
from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass
class Rng:
    """Thin wrapper around random.Random that we can pass around explicitly."""

    seed: int
    _r: random.Random | None = None

    def __post_init__(self) -> None:
        self._r = random.Random(self.seed)

    def chance(self, p: float) -> bool:
        """Return True with probability p (0..1)."""
        return self._r.random() < p

    def randint(self, lo: int, hi: int) -> int:
        return self._r.randint(lo, hi)

    def choice(self, seq):
        return self._r.choice(seq)

    def uniform(self, lo: float, hi: float) -> float:
        return self._r.uniform(lo, hi)

    def fork(self, salt: int) -> "Rng":
        """Create a child RNG. Useful for isolating subsystems so adding a new
        event in one place doesn't shift all downstream rolls."""
        return Rng(seed=self.seed ^ (salt * 0x9E3779B1))
