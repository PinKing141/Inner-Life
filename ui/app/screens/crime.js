/**
 * App.openSpecialCareersModal — the "Special Careers" overlay launched
 * from the Life screen's Occupation block. Surfaces the crime ladder
 * (and the prison panel when incarcerated). Crime events still land in
 * The Record; this overlay is just the entry point for committing one.
 */
(function (App) {
  "use strict";

  App.openSpecialCareersModal = function () {
    const s = this.state;
    if (!s) return;
    const incarcerated = s.crime && s.crime.is_incarcerated;

    if (incarcerated) {
      const served = s.crime.years_served || 0;
      const total = s.crime.sentence_years || 0;
      LifeUI.modal({
        kind: "notice", title: "Special Careers", dismissable: true,
        blocks: [{
          type: "list",
          items: [{
            icon: "lock", accent: "var(--c-bad)",
            title: `Prison — Year ${served} of ${total}`,
            subtitle: "Your life resumes when you walk out. Age up to serve time.",
            locked: true,
          }],
        }],
        actions: [{ label: "Close", variant: "ghost", action: "__close" }],
      });
      return;
    }

    const items = (s.crimes || []).map(c => {
      const pct = Math.round((c.success_chance || 0) * 100);
      const [lo, hi] = c.payout_range || [0, 0];
      const payoutStr = hi === 0
        ? "no payout"
        : `£${lo.toLocaleString()}–£${hi.toLocaleString()}`;
      return {
        icon: "gem",
        accent: c.available ? "var(--gold)" : "var(--ink-faint)",
        title: c.name,
        subtitle: `${c.blurb}  ·  ${payoutStr}  ·  ${c.sentence_years}y if caught`,
        locked: !c.available,
        action: c.available ? "commit-crime" : null,
        payload: c.id,
        trailing: c.available
          ? { kind: "badge", text: `${pct}% chance` }
          : { kind: "badge", text: c.min_age ? "Age " + c.min_age : "—", icon: "lock" },
      };
    });

    const blocks = [{ type: "list", items, emptyText: "No special careers available yet." }];
    if (s.crime && s.crime.past_offences && s.crime.past_offences.length) {
      blocks.push({ type: "section", label: "Record", count: s.crime.past_offences.length });
      blocks.push({
        type: "list",
        items: s.crime.past_offences.map(o => ({
          icon: "pen", accent: "var(--c-bad)",
          title: o, subtitle: "On your permanent record.",
        })),
      });
    }

    LifeUI.modal({
      kind: "neutral", title: "Special Careers", dismissable: true,
      blocks,
      actions: [{ label: "Close", variant: "ghost", action: "__close" }],
    });
  };
})(window.App = window.App || {});
