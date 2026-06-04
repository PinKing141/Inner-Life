/**
 * App.modals.death — End-of-life modal, with optional heir hand-off.
 *
 * When the snapshot lists eligible_heirs, each becomes a tappable
 * "Continue as your child" row that routes through continue-as-heir
 * to start the next generation.
 */
(function (App) {
  "use strict";

  App.raiseDeathModal = function (s) {
    const ch = s.character || {};
    const heirs = s.eligible_heirs || [];
    const blocks = [{ type: "award", icon: "hourglass",
      title: `${ch.name || "You"} died at ${ch.age || 0}`,
      subtitle: heirs.length
        ? "Your line endures — choose an heir to carry on."
        : "Your story is complete. Open the menu to start another life." }];

    if (heirs.length) {
      blocks.push({ type: "list", items: heirs.map(h => ({
        icon: "infant", accent: "var(--gold)",
        title: `${h.name} — age ${h.age}`,
        subtitle: `Continue as your child`,
        trailing: { kind: "chevron" },
        action: "continue-as-heir", payload: h.npc_id,
      })) });
    }

    LifeUI.modal({
      kind: "award", title: "End of Life", dismissable: true,
      blocks,
      actions: [{ label: "Close", variant: "ghost", action: "__close" }],
    });
  };
})(window.App = window.App || {});
