"""Qt WebEngine bridge.

Exposes the GameController to JavaScript through QWebChannel. The JS side
imports qwebchannel.js (shipped with PySide6), instantiates the channel, and
calls bridge methods which then mutate state in Python.

This is the same shape as the basketball career game's LiveGameService —
Python owns the simulation, JS owns the visuals, communication is one method
call at a time plus a state-broadcast slot.
"""
from __future__ import annotations

import json

from PySide6.QtCore import QObject, Signal, Slot

from controller import GameController


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
        self.stateChanged.emit(json.dumps(payload))

    # ---- Slots callable from JS ----

    @Slot(result=str)
    def snapshot(self) -> str:
        return json.dumps(self._controller.snapshot())

    @Slot(str, str, str, str, result=str)
    def newGame(self, name: str, gender: str, country: str, talent: str) -> str:
        return json.dumps(self._controller.new_game(name, gender, country, talent))

    @Slot(result=str)
    def ageUp(self) -> str:
        return json.dumps(self._controller.age_up())

    @Slot(int, result=str)
    def choose(self, choice_index: int) -> str:
        return json.dumps(self._controller.choose(choice_index))

    @Slot(str, result=str)
    def applyForJob(self, job_id: str) -> str:
        return json.dumps(self._controller.apply_for_job(job_id))

    @Slot(str, result=str)
    def activity(self, kind: str) -> str:
        return json.dumps(self._controller.activity(kind))
