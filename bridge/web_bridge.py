"""Qt WebEngine bridge.

Exposes the GameController to JavaScript through QWebChannel. The JS side
imports qwebchannel.js (shipped with PySide6), instantiates the channel, and
calls bridge methods which then mutate state in Python.

This is the same shape as the basketball career game's LiveGameService —
Python owns the simulation, JS owns the visuals, communication is one method
call at a time plus a state-broadcast slot.
"""
from __future__ import annotations

import dataclasses
import json
from enum import Enum

from PySide6.QtCore import QObject, Signal, Slot

from controller import GameController


def _json_default(obj):
    """Safety net for anything in the snapshot that isn't natively JSON-able.

    The core has been growing — predicates, conditions, enums — and any new
    object that finds its way into the snapshot tree shouldn't kill the whole
    UI. Best-effort: unwrap dataclasses, enums, sets; everything else degrades
    to a string with its class name so the UI can still render the rest.
    """
    if dataclasses.is_dataclass(obj):
        return dataclasses.asdict(obj)
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, (set, frozenset)):
        return list(obj)
    to_dict = getattr(obj, "to_dict", None)
    if callable(to_dict):
        try:
            return to_dict()
        except Exception:
            pass
    return {"__type__": type(obj).__name__, "repr": repr(obj)}


def _dumps(payload) -> str:
    return json.dumps(payload, default=_json_default)


class WebBridge(QObject):
    """Object exposed to JS as `bridge`.

    JS calls: bridge.newGame(...), bridge.ageUp(), bridge.choose(i),
              bridge.applyForJob(jobId), bridge.activity(kind).
    JS listens for: bridge.stateChanged.connect(payload => ...).
    """

    stateChanged = Signal(str)  # JSON string

    def __init__(self, controller: GameController, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        # Forward controller broadcasts to JS as JSON.
        self._controller.subscribe(self._emit_state)

    def _emit_state(self, payload: dict) -> None:
        self.stateChanged.emit(_dumps(payload))

    # ---- Slots callable from JS ----

    @Slot(result=str)
    def snapshot(self) -> str:
        return _dumps(self._controller.snapshot())

    @Slot(str, str, str, str, result=str)
    def newGame(self, name: str, gender: str, country: str, talent: str) -> str:
        return _dumps(self._controller.new_game(name, gender, country, talent))

    @Slot(str, str, str, str, str, str, result=str)
    def newGameFull(
        self,
        first_name: str,
        last_name: str,
        gender: str,
        country: str,
        city: str,
        talent: str,
    ) -> str:
        """Phase: name split into first/last + city. Preferred call from JS."""
        full = f"{first_name} {last_name}".strip()
        return json.dumps(self._controller.new_game(
            name=full,
            gender=gender,
            country=country,
            talent=talent,
            first_name=first_name,
            last_name=last_name,
            city=city,
        ))

    @Slot(result=str)
    def ageUp(self) -> str:
        return _dumps(self._controller.age_up())

    @Slot(int, result=str)
    def choose(self, choice_index: int) -> str:
        return _dumps(self._controller.choose(choice_index))

    @Slot(str, result=str)
    def applyForJob(self, job_id: str) -> str:
        return _dumps(self._controller.apply_for_job(job_id))

    @Slot(int, str, result=str)
    def relationshipAction(self, npc_id: int, action: str) -> str:
        return _dumps(self._controller.relationship_action(npc_id, action))

    @Slot(result=str)
    def workHarder(self) -> str:
        return _dumps(self._controller.work_harder())

    @Slot(result=str)
    def acknowledgeJobOffer(self) -> str:
        return _dumps(self._controller.acknowledge_job_offer())

    @Slot(result=str)
    def acknowledgePromotion(self) -> str:
        return _dumps(self._controller.acknowledge_promotion())

    @Slot(result=str)
    def clearApplicationError(self) -> str:
        return _dumps(self._controller.clear_application_error())

    @Slot(bool, str, result=str)
    def setUniversityPlan(self, attend: bool, major: str) -> str:
        return _dumps(self._controller.set_university_plan(attend, major))

    @Slot(result=str)
    def acknowledgeDegree(self) -> str:
        return _dumps(self._controller.acknowledge_degree())

    @Slot(result=str)
    def dropOutUniversity(self) -> str:
        return _dumps(self._controller.drop_out_university())

    @Slot(int, result=str)
    def answerExam(self, choice_index: int) -> str:
        return _dumps(self._controller.answer_exam(choice_index))

    @Slot(result=str)
    def cheatExam(self) -> str:
        return _dumps(self._controller.cheat_exam())

    @Slot(result=str)
    def applyUniversity(self) -> str:
        return _dumps(self._controller.apply_university_now())

    @Slot(str, result=str)
    def enrollPostgrad(self, program: str) -> str:
        return _dumps(self._controller.enroll_postgrad(program))

    @Slot(str, result=str)
    def activity(self, kind: str) -> str:
        return _dumps(self._controller.activity(kind))


