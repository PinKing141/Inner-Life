"""GameController.

Sits between the deterministic core and any presentation layer (Qt bridge,
Rich CLI, future API server). Holds the current GameState and exposes the
verbs the UI cares about: start a new life, age up, pick an event choice,
apply for jobs, do activities.

The controller is NOT deterministic in the way the core is — it can talk to
the filesystem (save/load), time, etc. Keep that limited to here.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Callable

from core import economy, relationships, sim
from core.content import countries as countries_mod
from core.state import FeedEntry, GameState


class GameController:
    def __init__(self) -> None:
        self.state: GameState | None = None
        # Subscribers receive the full state-as-dict after each mutation.
        self._listeners: list[Callable[[dict], None]] = []

    # ---- Subscription ----

    def subscribe(self, fn: Callable[[dict], None]) -> None:
        self._listeners.append(fn)

    def _broadcast(self) -> None:
        if self.state is None:
            return
        payload = self.snapshot()
        for fn in self._listeners:
            fn(payload)

    # ---- Snapshot for the UI ----

    def snapshot(self) -> dict:
        """The single source of truth that gets sent to the UI."""
        if self.state is None:
            return {"mode": "CREATION", "countries": self._countries_for_ui()}
        snap = self.state.to_dict()
        snap["pending_event"] = sim.get_pending_event(self.state)
        snap["jobs"] = [
            {
                "job_id": j.job_id, "title": j.title, "min_age": j.min_age,
                "min_smarts": j.min_smarts, "salary": j.salary,
                "track": getattr(j, "track", "general"),
            }
            for j in economy.list_jobs()
        ]
        snap["countries"] = self._countries_for_ui()
        if self.state.character is not None:
            country = countries_mod.resolve(self.state.character.country)
            snap["country_flag"] = country.flag
            snap["country_code"] = country.code
            snap["currency"] = country.currency
        return snap

    def _countries_for_ui(self) -> list[dict]:
        return [
            {"code": c.code, "name": c.name, "flag": c.flag, "currency": c.currency, "cities": list(c.cities)}
            for c in countries_mod.list_countries()
        ]

    # ---- Verbs the UI calls ----

    def new_game(
        self,
        name: str,
        gender: str,
        country: str,
        talent: str,
        seed: int | None = None,
        *,
        first_name: str | None = None,
        last_name: str | None = None,
        city: str | None = None,
    ) -> dict:
        if seed is None:
            seed = int(time.time() * 1000) & 0x7FFFFFFF
        self.state = sim.new_game(
            seed=seed,
            name=name,
            gender=gender,
            country=country,
            talent=talent,
            first_name=first_name,
            last_name=last_name,
            city=city,
        )
        self._broadcast()
        return self.snapshot()

    def age_up(self) -> dict:
        if self.state is not None:
            sim.age_up(self.state)
            self._broadcast()
        return self.snapshot()

    def choose(self, choice_index: int) -> dict:
        if self.state is not None:
            sim.resolve_choice(self.state, choice_index)
            self._broadcast()
        return self.snapshot()

    def apply_for_job(self, job_id: str) -> dict:
        if self.state is None:
            return self.snapshot()
        ok, msg = economy.apply_for_job(self.state, job_id)
        self.state.feed.append(FeedEntry(
            age=self.state.character.age if self.state.character else 0,
            text=msg,
            kind="good" if ok else "bad",
            entry_id=f"feed:job:{self.state.tick}:{job_id}",
        ))
        self._broadcast()
        return self.snapshot()

    def activity(self, kind: str) -> dict:
        if self.state is None or self.state.character is None:
            return self.snapshot()
        s = self.state
        age = s.character.age
        log: str
        ok = True
        if kind == "study":
            s.stats.smarts = min(100, s.stats.smarts + 2)
            s.stats.happiness = max(0, s.stats.happiness - 2)
            log = "You studied hard. You feel smarter, but a bit bored."
        elif kind == "gym":
            if s.money < 30:
                ok = False
                log = "You cannot afford the gym."
            else:
                s.money -= 30
                s.stats.health = min(100, s.stats.health + 3)
                s.stats.looks = min(100, s.stats.looks + 1)
                log = "You went to the gym. It cost £30."
        elif kind == "doctor":
            if s.money < 100:
                ok = False
                log = "You cannot afford a private doctor."
            else:
                s.money -= 100
                s.stats.health = min(100, s.stats.health + 15)
                log = "You visited a private doctor. It cost £100 but you feel much better."
        elif kind == "spend_time":
            relationships.spend_time_with_family(s)
            s.stats.happiness = min(100, s.stats.happiness + 5)
            log = "You spent quality time with your family."
        else:
            return self.snapshot()

        s.feed.append(FeedEntry(
            age=age, text=log, kind="good" if ok else "bad",
            entry_id=f"feed:act:{s.tick}:{kind}",
        ))
        self._broadcast()
        return self.snapshot()

    # ---- Save / load ----

    def save(self, path: Path) -> None:
        if self.state is None:
            return
        path.write_text(json.dumps(self.snapshot(), indent=2, default=str))

    def load(self, path: Path) -> dict:
        """Phase 7 — rebuild a full GameState from a JSON snapshot on disk."""
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        # Snapshots from `save()` are decorated with UI fields (jobs, pending_event,
        # countries, …); GameState.from_dict ignores the extras.
        self.state = GameState.from_dict(data)
        self._broadcast()
        return self.snapshot()
