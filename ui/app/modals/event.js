/**
 * App.modals.event — the random-event choice modal.
 *
 * Driven by snapshot.pending_event. Choice indexes route through
 * `event-choice` → bridge.choose(i).
 */
(function (App) {
  "use strict";

  App.raiseEventModal = function (ev) {
    LifeUI.modal({
      kind: "event", title: ev.title || "A Decision",
      blocks: [
        { type: "text", text: ev.text || "" },
        { type: "choices", action: "event-choice",
          choices: (ev.choices || []).map((c, i) => ({ id: i, label: c.text || "" })) },
      ],
    });
  };
})(window.App = window.App || {});
