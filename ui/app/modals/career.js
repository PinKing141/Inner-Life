/**
 * App.modals.career — job-offer / promotion / loss / setback / rejection.
 *
 * Five small modals that announce career mutations the player didn't
 * directly initiate. Each acks through a distinct dispatch action.
 */
(function (App) {
  "use strict";

  App.raiseJobOfferModal = function (o) {
    LifeUI.modal({
      kind: "offer",
      title: `${o.title}${o.employer ? " — " + o.employer : ""}`,
      blocks: [
        { type: "text", text: `You were offered a position as a ${o.title}.` },
        { type: "deltas", deltas: [
          { label: "Salary", value: `£${(o.salary || 0).toLocaleString()} / yr`, tone: "good" },
        ] },
      ],
      actions: [{ label: "Acknowledge", variant: "primary", action: "ack-job-offer" }],
    });
  };

  App.raisePromotionModal = function (p) {
    LifeUI.modal({
      kind: "award", title: "Promoted",
      blocks: [{ type: "award", icon: "trophy", title: p.title,
        subtitle: `${p.employer || ""} · £${(p.salary || 0).toLocaleString()} (+${p.pct}%)` }],
      actions: [{ label: "Excellent", variant: "primary", action: "ack-promotion" }],
    });
  };

  App.raiseJobLossModal = function (l) {
    LifeUI.modal({
      kind: "notice",
      title: l.fired ? "You Were Fired" : "You Were Laid Off",
      blocks: [{ type: "text", text:
        `You lost your position as ${l.title} at ${l.employer || "your employer"} — ${l.reason || "let go"}.` }],
      actions: [{ label: "Acknowledge", variant: "ghost", action: "ack-job-loss" }],
    });
  };

  App.raiseSetbackModal = function (c) {
    LifeUI.modal({
      kind: "notice",
      title: c.type === "demotion" ? "Demoted" : "Pay Cut",
      blocks: [{ type: "text", text:
        c.type === "demotion"
          ? `You were demoted to ${c.title} (−${c.pct}%).`
          : `Your salary was cut by ${c.pct}% (${c.reason || ""}).` }],
      actions: [{ label: "Acknowledge", variant: "ghost", action: "ack-setback" }],
    });
  };

  App.raiseRejectionModal = function (msg) {
    LifeUI.modal({
      kind: "notice", title: "Application Rejected", dismissable: true,
      blocks: [{ type: "text", text: msg || "" }],
      actions: [{ label: "Close", variant: "ghost", action: "clear-rejection" }],
    });
  };
})(window.App = window.App || {});
