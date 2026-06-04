/**
 * App.modals.relations — relationship profile + gift / money pickers.
 *
 * openRelationProfile builds the per-NPC profile modal with three
 * verb sections (Conversation / Spending / Conflict). The picker
 * sub-modals (openGiftPicker / openMoneyGiftPicker) consume the
 * snapshot's gift_catalogue and money_gift_tiers respectively;
 * tapping a row dispatches `rel-interact-param` with the chosen id.
 */
(function (App) {
  "use strict";

  App.openRelationProfile = function (npcId) {
    const r = (this.state.relationships || []).find(x => x.npc_id === npcId);
    if (!r) return;
    LifeUI.modal({
      kind: "profile", title: r.name, dismissable: true,
      eyebrow: r.kind,
      blocks: [
        { type: "text", text: `${r.kind} · ${r.alive ? "Living" : "Deceased"}` },
        { type: "deltas", deltas: [{ label: "Relationship",
          value: r.relationship + " / 100",
          tone: r.relationship >= 66 ? "good" : r.relationship >= 33 ? "" : "bad" }] },
        ...(r.alive ? [
          { type: "section", label: "Conversation" },
          { type: "list", items: [
            { icon: "heart", accent: "var(--c-good)", title: "Talk",
              subtitle: "A nice chat",
              trailing: { kind: "chevron" }, action: "rel-interact",
              payload: { npc_id: npcId, action: "talk" } },
            { icon: "spark", accent: "var(--c-happy)", title: "Compliment",
              subtitle: "A small lift",
              trailing: { kind: "chevron" }, action: "rel-interact",
              payload: { npc_id: npcId, action: "compliment" } },
            { icon: "moon", accent: "var(--c-smarts)", title: "Conversation",
              subtitle: "A real talk — sometimes lands, sometimes drains",
              trailing: { kind: "chevron" }, action: "rel-interact",
              payload: { npc_id: npcId, action: "conversation" } },
            { icon: "book", accent: "var(--c-smarts)", title: "Ask for advice",
              subtitle: "Smarter NPCs give better counsel",
              trailing: { kind: "chevron" }, action: "rel-interact",
              payload: { npc_id: npcId, action: "ask_advice" } },
            { icon: "check", accent: "var(--c-good)", title: "Apologise",
              subtitle: "Best when relationship is hurt",
              trailing: { kind: "chevron" }, action: "rel-interact",
              payload: { npc_id: npcId, action: "apologize" } },
            { icon: "happy", accent: "var(--c-happy)", title: "Hang out",
              subtitle: "Free, reliable, +rel +happiness",
              trailing: { kind: "chevron" }, action: "rel-interact",
              payload: { npc_id: npcId, action: "hang_out" } },
          ] },
          { type: "section", label: "Spending" },
          { type: "list", items: [
            { icon: "gem", accent: "var(--gold)", title: "Give a gift",
              subtitle: "Pick something — from a handmade card to luxury jewellery",
              trailing: { kind: "chevron" }, action: "open-gift-picker",
              payload: { npc_id: npcId } },
            { icon: "brief", accent: "var(--cat-money)", title: "Give money",
              subtitle: "Pick an amount to hand over",
              trailing: { kind: "chevron" }, action: "open-money-gift-picker",
              payload: { npc_id: npcId } },
            { icon: "brief", accent: "var(--cat-money)", title: "Borrow money",
              subtitle: "Needs a strong relationship",
              trailing: { kind: "chevron" }, action: "rel-interact",
              payload: { npc_id: npcId, action: "borrow_money" } },
          ] },
          { type: "section", label: "Conflict" },
          { type: "list", items: [
            { icon: "x", accent: "var(--c-warn)", title: "Argue",
              subtitle: "Costs the relationship",
              trailing: { kind: "chevron" }, action: "rel-interact",
              payload: { npc_id: npcId, action: "argue" } },
            { icon: "x", accent: "var(--c-bad)", title: "Insult",
              subtitle: "Costs more, costs longer",
              trailing: { kind: "chevron" }, action: "rel-interact",
              payload: { npc_id: npcId, action: "insult" } },
          ] },
        ] : []),
      ],
      actions: [{ label: "Close", variant: "ghost", action: "__close" }],
    });
  };

  // Sub-modal: pick a gift from the catalogue (snap.gift_catalogue).
  // Each row shows the gift's name, blurb, and price. Locked when the
  // player can't afford it (badge says so); tapping fires
  // `rel-interact-param` with the matching gift_id as `param`.
  App.openGiftPicker = function (npcId) {
    const r = (this.state.relationships || []).find(x => x.npc_id === npcId);
    if (!r) return;
    const money = this.state.money || 0;
    const gifts = this.state.gift_catalogue || [];
    const items = gifts.map(g => {
      const free = g.price === 0;
      const afford = money >= g.price;
      return {
        icon: free ? "spark" : "gem",
        accent: afford ? (free ? "var(--c-happy)" : "var(--gold)") : "var(--ink-faint)",
        title: g.name,
        subtitle: g.blurb,
        locked: !afford,
        action: afford ? "rel-interact-param" : null,
        payload: afford ? { npc_id: npcId, action: "give_gift", param: g.id } : null,
        trailing: afford
          ? { kind: "value", text: free ? "Free" : ("£" + g.price.toLocaleString()) }
          : { kind: "badge", text: "£" + g.price.toLocaleString(), icon: "lock" },
      };
    });
    LifeUI.modal({
      kind: "picker", title: `Gift for ${r.name}`, dismissable: true,
      blocks: [{ type: "list", items }],
      actions: [{ label: "Close", variant: "ghost", action: "__close" }],
    });
  };

  // Sub-modal: pick a money-gift tier (snap.money_gift_tiers). Same
  // pattern as gifts — locked rows show why; tap fires rel-interact
  // with the tier id.
  App.openMoneyGiftPicker = function (npcId) {
    const r = (this.state.relationships || []).find(x => x.npc_id === npcId);
    if (!r) return;
    const money = this.state.money || 0;
    const tiers = this.state.money_gift_tiers || [];
    const items = tiers.map(t => {
      const afford = money >= t.amount;
      return {
        icon: "brief",
        accent: afford ? "var(--cat-money)" : "var(--ink-faint)",
        title: "£" + t.amount.toLocaleString(),
        subtitle: t.blurb,
        locked: !afford,
        action: afford ? "rel-interact-param" : null,
        payload: afford ? { npc_id: npcId, action: "give_money", param: t.id } : null,
        trailing: afford
          ? { kind: "chevron" }
          : { kind: "badge", text: "Need £" + t.amount.toLocaleString(), icon: "lock" },
      };
    });
    LifeUI.modal({
      kind: "picker", title: `Give money to ${r.name}`, dismissable: true,
      blocks: [{ type: "list", items }],
      actions: [{ label: "Close", variant: "ghost", action: "__close" }],
    });
  };
})(window.App = window.App || {});
