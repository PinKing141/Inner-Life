/**
 * App.modals.birth — the "It's a baby!" naming modal.
 *
 * Driven by snapshot.pending_birth. Pre-fills a suggested name in a
 * text-input block; tap "Name them" → name-baby with the npc_id.
 */
(function (App) {
  "use strict";

  App.raiseBirthModal = function (b) {
    if (!b) return;
    const descriptor = (b.gender === "Female") ? "girl"
                     : (b.gender === "Male") ? "boy" : "child";
    const partner = b.partner_name || "your partner";
    LifeUI.modal({
      kind: "award", title: "It's a baby!", dismissable: false,
      blocks: [
        { type: "award", icon: "heart",
          title: `You and ${partner} welcomed a baby ${descriptor}.`,
          subtitle: "What will you name them?" },
        { type: "text-input",
          key: "babyName",
          label: "First name",
          value: b.suggested_name || "",
          placeholder: "Their name",
          maxLength: 32 },
      ],
      actions: [
        { label: "Name them", variant: "primary", action: "name-baby",
          payload: { npc_id: b.npc_id } },
      ],
    });
  };
})(window.App = window.App || {});
