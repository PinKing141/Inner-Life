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

from core import activities, cars as cars_mod, crime as crime_mod, dating, economy, education, genealogy, housing, milestones, relationships, sim
from core.content import countries as countries_mod
from core.content import courses as courses_mod
from core.rng import Rng
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
                "min_education": getattr(j, "min_education", "None"),
                "track": getattr(j, "track", "general"),
                "required_field": getattr(j, "required_field", ""),
                "employer": economy.employer_for(self.state, j.job_id),
            }
            for j in economy.list_jobs()
        ]
        snap["courses"] = courses_mod.list_courses_for_ui()
        snap["activities"] = activities.list_descriptors()
        snap["exam"] = self._exam_for_ui()
        snap["housing_market"] = housing.list_market(self.state)
        # Cars/Assets v1: catalogue rows for the UI (availability per
        # age + money) + owned vehicles list.
        snap["car_market"] = cars_mod.list_market(self.state)
        snap["vehicles"] = cars_mod.list_owned(self.state)
        snap["net_worth"] = housing.net_worth(self.state)
        # Phase 5: the death modal reads eligible_heirs to decide whether
        # to offer "continue as [child]" buttons; ancestors carries the
        # outgoing lives so a future family-history UI can browse them.
        snap["eligible_heirs"] = genealogy.eligible_heirs(self.state)
        snap["ancestors"] = list(self.state.ancestors)
        # Crime v1: the Activities/Crime screen reads this to render the
        # crime ladder with live success chances. Includes computed
        # availability flag so under-age / incarcerated rows render greyed.
        snap["crimes"] = crime_mod.list_crimes_for_ui(self.state)
        snap["countries"] = self._countries_for_ui()
        if self.state.character is not None:
            country = countries_mod.resolve(self.state.character.country)
            snap["country_flag"] = country.flag
            # Resolve the on-disk SVG location under ui/flags-svg/** and emit a
            # path relative to the `ui/` folder so the frontend can load it.
            repo_root = Path(__file__).resolve().parents[1]
            ui_root = repo_root / "ui"
            code = country.code.lower()
            found = None
            for p in (ui_root / "flags-svg").rglob(f"{code}.svg"):
                found = p
                break
            if found:
                snap["country_flag_svg"] = str(found.relative_to(ui_root)).replace('\\', '/')
            else:
                snap["country_flag_svg"] = f"flags-svg/other/{code}.svg"
            snap["country_code"] = country.code
            snap["currency"] = country.currency
        return snap

    def _exam_for_ui(self) -> dict | None:
        """UI-safe view of the active exam — never leaks the answer key, only
        the answer for a question the player has successfully cheated on."""
        if self.state is None or self.state.exam is None:
            return None
        ex = self.state.exam
        qs = ex.get("questions", [])
        idx = ex.get("index", 0)
        current = None
        if 0 <= idx < len(qs):
            q = qs[idx]
            current = {"prompt": q["prompt"], "options": list(q["options"]), "subject": q.get("subject", "")}
        return {
            "index": idx,
            "total": len(qs),
            "current": current,
            "finished": ex.get("finished", False),
            "caught": ex.get("caught", False),
            "revealed": ex.get("revealed"),
        }

    def _countries_for_ui(self) -> list[dict]:
        repo_root = Path(__file__).resolve().parents[1]
        ui_root = repo_root / "ui"
        def resolve_svg(code: str) -> str:
            code_l = code.lower()
            for p in (ui_root / "flags-svg").rglob(f"{code_l}.svg"):
                return str(p.relative_to(ui_root)).replace('\\', '/')
            return f"flags-svg/other/{code_l}.svg"

        return [
            {
                "code": c.code,
                "name": c.name,
                "flag": c.flag,
                "flag_svg": resolve_svg(c.code),
                "currency": c.currency,
                "cities": list(c.cities),
            }
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

    def set_university_plan(self, attend: bool, major: str = "") -> dict:
        s = self.state
        if s is None or s.character is None:
            return self.snapshot()
        edu = s.education
        edu.university_intent = "attend" if attend else "skip"
        edu.university_major = major.strip() if attend else ""

        # Popup path: the player is being prompted right now at graduation, so
        # the decision takes effect immediately rather than pre-registering an
        # intent for a future secondary graduation.
        if edu.awaiting_university_choice:
            edu.awaiting_university_choice = False
            if attend:
                education.enroll_university(s)
                scholar = "" if edu.scholarship == "none" else f" on a {edu.scholarship} scholarship"
                text = f"You enrolled in {edu.university_major or 'an undeclared course'} at {edu.university_name}{scholar}."
            else:
                text = "You chose not to attend university. You can apply later from the Career tab."
        else:
            text = (
                f"You chose to attend university and study {edu.university_major or 'an undeclared subject'} after secondary graduation."
                if attend
                else "You chose not to attend university after secondary graduation."
            )

        s.feed.append(FeedEntry(
            age=s.character.age,
            text=text,
            kind="neutral",
            entry_id=f"feed:edu_plan:{s.tick}",
        ))
        self._broadcast()
        return self.snapshot()

    def acknowledge_degree(self) -> dict:
        if self.state is None or self.state.character is None:
            return self.snapshot()
        self.state.education.degree_award_pending = False
        self._broadcast()
        return self.snapshot()

    def _feed(self, text: str, kind: str, tag: str) -> None:
        s = self.state
        if s is None:
            return
        s.feed.append(FeedEntry(
            age=s.character.age if s.character else 0,
            text=text, kind=kind, entry_id=f"feed:{tag}:{s.tick}",
        ))

    def answer_exam(self, choice_index: int) -> dict:
        s = self.state
        if s is None or s.exam is None:
            return self.snapshot()
        ex = s.exam
        if ex.get("finished"):
            return self.snapshot()
        qs = ex["questions"]
        i = ex.get("index", 0)
        if i >= len(qs):
            return self.snapshot()
        ex["answers"].append(choice_index)
        if choice_index == qs[i]["answer"]:
            ex["correct"] += 1
        ex["revealed"] = None
        ex["index"] = i + 1
        if ex["index"] >= len(qs):
            msg = education.finalize_exam(s)
            self._feed(msg, "neutral", "exam_result")
        self._broadcast()
        return self.snapshot()

    def cheat_exam(self) -> dict:
        """Reveal the current answer — unless you're caught, which ends the exam."""
        s = self.state
        if s is None or s.exam is None:
            return self.snapshot()
        ex = s.exam
        if ex.get("finished"):
            return self.snapshot()
        rng = Rng(s.seed).fork(s.tick).fork(ex.get("index", 0) * 7 + 1)
        if rng.chance(0.40):
            ex["caught"] = True
            self._feed("You were caught cheating and thrown out of the exam.", "bad", "exam_cheat")
            msg = education.finalize_exam(s)
            self._feed(msg, "neutral", "exam_result")
        else:
            ex["revealed"] = ex["questions"][ex["index"]]["answer"]
        self._broadcast()
        return self.snapshot()

    def apply_university_now(self) -> dict:
        """Apply to university later (e.g. after declining at graduation)."""
        if self.state is None or self.state.character is None:
            return self.snapshot()
        edu = self.state.education
        if edu.in_school or edu.degree_completed or self.state.character.age < 18:
            return self.snapshot()
        if not edu.admitted_tier:
            # No place from the exam — adult education always offers community.
            edu.admitted_tier = "Community"
            edu.scholarship = "none"
        edu.university_intent = "undecided"
        edu.awaiting_university_choice = True
        self._broadcast()
        return self.snapshot()

    def work_harder(self) -> dict:
        if self.state is None or self.state.character is None:
            return self.snapshot()
        msg = economy.work_harder(self.state)
        self._feed(msg, "good" if self.state.career else "bad", "work")
        self._broadcast()
        return self.snapshot()

    def request_raise(self) -> dict:
        if self.state is None or self.state.character is None:
            return self.snapshot()
        ok, msg = economy.request_raise(self.state)
        self._feed(msg, "good" if ok else "bad", "raise")
        self._broadcast()
        return self.snapshot()

    def request_promotion(self) -> dict:
        if self.state is None or self.state.character is None:
            return self.snapshot()
        ok, msg, promo = economy.request_promotion(self.state)
        if promo is not None:
            self.state.pending_promotion = promo
        self._feed(msg, "good" if ok else "bad", "promo_request")
        self._broadcast()
        return self.snapshot()

    def quit_job(self) -> dict:
        if self.state is None or self.state.character is None:
            return self.snapshot()
        msg = economy.quit_job(self.state)
        self._feed(msg, "neutral", "quit")
        self._broadcast()
        return self.snapshot()

    def acknowledge_job_offer(self) -> dict:
        if self.state is not None:
            self.state.pending_job_offer = None
            self._broadcast()
        return self.snapshot()

    def acknowledge_job_loss(self) -> dict:
        if self.state is not None:
            self.state.pending_job_loss = None
            self._broadcast()
        return self.snapshot()

    def acknowledge_career_setback(self) -> dict:
        if self.state is not None:
            self.state.pending_career_setback = None
            self._broadcast()
        return self.snapshot()

    def acknowledge_promotion(self) -> dict:
        if self.state is not None:
            self.state.pending_promotion = None
            self._broadcast()
        return self.snapshot()

    def clear_application_error(self) -> dict:
        if self.state is not None:
            self.state.job_application_error = None
            self._broadcast()
        return self.snapshot()

    def acknowledge_milestone(self) -> dict:
        """Dismiss the current life-milestone modal (turning 18 / 30 / 50 …)."""
        if self.state is not None:
            milestones.acknowledge(self.state)
            self._broadcast()
        return self.snapshot()

    def enroll_postgrad(self, program: str) -> dict:
        """Begin a master's or doctorate from the Career tab."""
        if self.state is None or self.state.character is None:
            return self.snapshot()
        edu = self.state.education
        if edu.in_school:
            return self.snapshot()
        if program == "Master's Degree" and not edu.degree_completed:
            return self.snapshot()
        if program == "Doctorate" and not edu.masters_completed:
            return self.snapshot()
        if program not in education.PROGRAMS:
            return self.snapshot()
        education.enroll_program(self.state, program)
        label = education.PROGRAMS[program]["label"]
        self._feed(f"You enrolled in a {label} at {edu.university_name}.", "neutral", "postgrad")
        self._broadcast()
        return self.snapshot()

    def drop_out_university(self) -> dict:
        s = self.state
        if s is None or s.character is None:
            return self.snapshot()
        if s.education.level != "University" or not s.education.in_school:
            return self.snapshot()
        s.education.in_school = False
        s.education.university_dropped_out = True
        s.feed.append(FeedEntry(
            age=s.character.age,
            text="You dropped out of university.",
            kind="bad",
            entry_id=f"feed:edu_dropout:{s.tick}",
        ))
        self._broadcast()
        return self.snapshot()

    def buy_home(self, listing_id: str) -> dict:
        if self.state is None or self.state.character is None:
            return self.snapshot()
        ok, msg = housing.buy_home(self.state, listing_id)
        self._feed(msg, "good" if ok else "bad", "buy_home")
        self._broadcast()
        return self.snapshot()

    def buy_home_mortgage(self, listing_id: str) -> dict:
        if self.state is None or self.state.character is None:
            return self.snapshot()
        ok, msg = housing.buy_home_mortgage(self.state, listing_id)
        self._feed(msg, "good" if ok else "bad", "mortgage")
        self._broadcast()
        return self.snapshot()

    def rent_home(self, listing_id: str) -> dict:
        if self.state is None or self.state.character is None:
            return self.snapshot()
        ok, msg = housing.rent_home(self.state, listing_id)
        self._feed(msg, "good" if ok else "bad", "rent_home")
        self._broadcast()
        return self.snapshot()

    def sell_home(self, property_id: str) -> dict:
        if self.state is None or self.state.character is None:
            return self.snapshot()
        ok, msg = housing.sell_home(self.state, property_id)
        self._feed(msg, "good" if ok else "bad", "sell_home")
        self._broadcast()
        return self.snapshot()

    def stop_renting(self) -> dict:
        if self.state is None or self.state.character is None:
            return self.snapshot()
        ok, msg = housing.stop_renting(self.state)
        self._feed(msg, "neutral" if ok else "bad", "stop_rent")
        self._broadcast()
        return self.snapshot()

    # ---- Cars / Assets v1 ----

    def buy_car(self, car_id: str) -> dict:
        if self.state is None or self.state.character is None:
            return self.snapshot()
        ok, msg = cars_mod.buy_car(self.state, car_id)
        self._feed(msg, "good" if ok else "bad", "buy_car")
        self._broadcast()
        return self.snapshot()

    def sell_car(self, instance_id: int) -> dict:
        if self.state is None or self.state.character is None:
            return self.snapshot()
        ok, msg = cars_mod.sell_car(self.state, instance_id)
        self._feed(msg, "good" if ok else "bad", "sell_car")
        self._broadcast()
        return self.snapshot()

    def relationship_action(self, npc_id: int, action: str) -> dict:
        if self.state is None or self.state.character is None:
            return self.snapshot()
        ok, msg = relationships.interact(self.state, npc_id, action)
        self._feed(msg, "good" if ok else "bad", f"rel:{npc_id}:{action}")
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


    def continue_as_heir(self, npc_id: int) -> dict:
        """Phase 5: transition the playable across a generational boundary.

        Routes through genealogy.continue_as_heir, which archives the
        current Character into state.ancestors, swaps in a fresh
        Character built from the heir's Agent record, applies the
        estate share, and flips mode back to PLAYING. No-op if the
        engine refuses (not in DEATH, heir unknown, heir dead)."""
        if self.state is None:
            return self.snapshot()
        genealogy.continue_as_heir(self.state, npc_id)
        self._broadcast()
        return self.snapshot()

    # ---- Pregnancy v1 ----

    def try_for_baby(self) -> dict:
        """Player-initiated conception attempt. Routes through
        ``genealogy.attempt_conception`` (probabilistic, like the
        broken_condom event) so the outcome is age/health-weighted.
        Writes a feed entry either way so the player gets feedback."""
        if self.state is None or self.state.character is None:
            return self.snapshot()
        rng = Rng(self.state.seed).fork(self.state.tick).fork(len(self.state.feed)).fork(0x7B7B)
        ok = genealogy.attempt_conception(self.state, rng)
        msg = (
            "You and your partner began trying. Now you wait."
            if ok else
            "You and your partner tried this month. Nothing yet."
        )
        self.state.feed.append(FeedEntry(
            age=self.state.character.age,
            text=msg,
            kind="special" if ok else "neutral",
            entry_id=f"feed:try_baby:{self.state.tick}:{len(self.state.feed)}",
        ))
        self._broadcast()
        return self.snapshot()

    def name_baby(self, npc_id: int, chosen_name: str) -> dict:
        """Apply the player's chosen name to a newly-born child.
        Clears the ``pending_birth`` modal payload on success."""
        if self.state is None:
            return self.snapshot()
        genealogy.name_child(self.state, npc_id, chosen_name)
        self._broadcast()
        return self.snapshot()

    # ---- Love/Dating v1 ----

    def _dating_verb(self, fn_name: str) -> dict:
        """Dispatcher for the four dating verbs. Each verb runs the core
        function with a forked RNG, writes a feed entry, and broadcasts.
        Refusals (ok=False) still surface in the feed as 'neutral' so the
        player sees why the tap didn't work."""
        if self.state is None or self.state.character is None:
            return self.snapshot()
        fn = getattr(dating, fn_name)
        # Fork off the current tick so repeated calls in one year still
        # diverge (date #2 isn't a re-roll of date #1).
        rng_seed_extra = len(self.state.feed)
        rng = Rng(self.state.seed).fork(self.state.tick).fork(rng_seed_extra).fork(0xDA1E)
        # `become_official` and `break_up` take no rng.
        if fn_name in ("become_official", "break_up"):
            ok, msg = fn(self.state)
        else:
            ok, msg = fn(self.state, rng)
        self.state.feed.append(FeedEntry(
            age=self.state.character.age,
            text=msg,
            kind="good" if ok else "neutral",
            entry_id=f"feed:dating:{fn_name}:{self.state.tick}:{rng_seed_extra}",
        ))
        self._broadcast()
        return self.snapshot()

    def ask_someone_out(self) -> dict:
        return self._dating_verb("ask_someone_out")

    def go_on_date(self) -> dict:
        return self._dating_verb("go_on_date")

    def become_official(self) -> dict:
        return self._dating_verb("become_official")

    def break_up(self) -> dict:
        return self._dating_verb("break_up")

    # ---- Crime v1 ----

    def commit_crime(self, crime_id: str) -> dict:
        """Attempt a crime from the catalogue. Routes through
        ``crime.attempt_crime`` with a forked rng; the outcome modal
        payload lands on ``state.pending_crime_outcome`` for the UI to
        raise. Refuses politely if the player is already incarcerated."""
        if self.state is None or self.state.character is None:
            return self.snapshot()
        rng = Rng(self.state.seed).fork(self.state.tick).fork(
            len(self.state.feed)
        ).fork(0xC2114E)
        crime_mod.attempt_crime(self.state, crime_id, rng)
        self._broadcast()
        return self.snapshot()

    def acknowledge_crime_outcome(self) -> dict:
        """Dismiss the crime outcome modal (clean getaway or busted).
        Just clears ``pending_crime_outcome`` so the modal closes."""
        if self.state is not None:
            self.state.pending_crime_outcome = None
            self._broadcast()
        return self.snapshot()

    def activity(self, kind: str) -> dict:
        s = self.state
        if s is None or s.character is None:
            return self.snapshot()
        # Crime v1: most free-world verbs make no sense from a cell. The
        # refusal feed line is visible to the player so they know why
        # the tap didn't work.
        if s.crime.is_incarcerated:
            s.feed.append(FeedEntry(
                age=s.character.age,
                text="You can't do that from a prison cell.",
                kind="neutral",
                entry_id=f"feed:act_blocked:{s.tick}:{kind}",
            ))
            self._broadcast()
            return self.snapshot()
        fn = activities.BY_KIND.get(kind)
        if fn is None:
            return self.snapshot()
        ok, log = fn(s)
        s.feed.append(FeedEntry(
            age=s.character.age, text=log, kind="good" if ok else "bad",
            entry_id=f"feed:act:{s.tick}:{kind}",
        ))
        self._broadcast()
        return self.snapshot()

    # ---- Save / load ----

    def save(self, path: Path) -> None:
        """Persist the CANONICAL state. Atomic: write to a temp file in the
        same directory and rename, so a crash mid-write never leaves a
        corrupt save in place. Raises OSError on I/O failure — callers
        (bridge / CLI) translate to user-facing messages."""
        if self.state is None:
            raise RuntimeError("no active game to save")
        path.parent.mkdir(parents=True, exist_ok=True)
        # to_dict() is the serialization contract that from_dict() inverts
        # exactly; snapshot() is UI-decorated and would corrupt round-trips.
        payload = json.dumps(self.state.to_dict(), indent=2, default=str)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(payload, encoding="utf-8")
        tmp.replace(path)

    def load(self, path: Path) -> dict:
        """Rebuild a full GameState from a canonical state dict on disk.
        Raises OSError on read failure, ValueError on parse / shape failure."""
        if not path.exists():
            raise FileNotFoundError(f"save file not found: {path}")
        raw = path.read_text(encoding="utf-8")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"save file is not valid JSON: {e}") from e
        # Valid JSON isn't enough — `from_dict` calls `.get(...)` on the root,
        # so a JSON array, string, or null would raise AttributeError and slip
        # past both this layer and the bridge envelope. Pin the contract here.
        if not isinstance(data, dict):
            raise ValueError(
                f"save file root must be a JSON object, got {type(data).__name__}"
            )
        try:
            self.state = GameState.from_dict(data)
        except (KeyError, TypeError, ValueError, AttributeError) as e:
            raise ValueError(f"save file is unreadable (schema mismatch): {e}") from e
        self._broadcast()
        return self.snapshot()
