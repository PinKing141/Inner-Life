/**
 * App.modals.milestone — 18/30/50/65/100 milestone congratulation modal.
 *
 * Icon + accent per milestone "kind". Adding a new milestone kind:
 * extend MILESTONE_LOOK (no other change needed — sim writes a kind
 * field that maps directly to the look table).
 */
(function (App) {
  "use strict";

  const MILESTONE_LOOK = {
    coming_of_age: { icon: "key",         accent: "var(--gold)" },
    decade:        { icon: "cake",        accent: "var(--accent)" },
    retirement:    { icon: "rocking",     accent: "var(--accent)" },
    centenarian:   { icon: "crown",       accent: "var(--gold)" },
  };

  App.raiseMilestoneModal = function (m) {
    if (!m) return;
    const look = MILESTONE_LOOK[m.kind] || { icon: "star", accent: "var(--accent)" };
    LifeUI.modal({
      kind: "award", title: m.title || "A milestone", dismissable: true,
      blocks: [{ type: "award", icon: look.icon,
        title: m.title || "",
        subtitle: m.subtitle || "" }],
      actions: [{ label: "Carry on", variant: "primary", action: "ack-milestone" }],
    });
  };
})(window.App = window.App || {});
