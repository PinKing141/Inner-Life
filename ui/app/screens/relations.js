/**
 * App.screens.relations — render the Relations tab + Love Life action row.
 *
 * Layout: state-aware "Love Life" group at the top, then Partner /
 * Dating / Family / Friends & Coworkers groups. Tapping a person opens
 * the relation profile modal (see ui/app/modals/relations.js).
 */
(function (App) {
  "use strict";

  App.renderRelations = function () {
    const s = this.state;
    const all = s.relationships || [];
    const partner = all.filter(r => r.kind === "Partner");
    const dating = all.filter(r => r.kind === "Dating");
    const family = all.filter(r => ["Mother", "Father", "Sibling"].includes(r.kind));
    const friends = all.filter(r => ["Friend", "Coworker"].includes(r.kind));
    const mk = (r) => ({
      icon: (r.kind === "Partner" || r.kind === "Dating") ? "heart" : "person",
      accent: r.alive
        ? ((r.kind === "Partner" || r.kind === "Dating") ? "var(--c-looks)" : "var(--cat-family)")
        : "var(--ink-faint)",
      title: r.name + (r.alive ? "" : " (deceased)"),
      subtitle: `${(r.kind || "").toUpperCase()}`,
      trailing: { kind: "meter", value: r.relationship,
        color: r.relationship >= 66 ? "var(--c-good)" :
               r.relationship >= 33 ? "var(--c-warn)" : "var(--c-bad)" },
      action: r.alive ? "open-relation" : null,
      payload: r.npc_id,
    });
    LifeUI.renderScreen("relations", [
      { label: "Love Life", items: this._loveLifeItems(s) },
      { label: "Partner", emptyText: "No partner yet.", items: partner.map(mk) },
      { label: "Dating", emptyText: "Not currently dating.", items: dating.map(mk) },
      { label: "Family", emptyText: "No family on record.", items: family.map(mk) },
      { label: "Friends & Coworkers", emptyText: "No close ties yet.", items: friends.map(mk) },
    ]);
  };

  // Build the action rows shown in the "Love Life" group of the Relations
  // screen. The set of buttons depends on whether the player is single,
  // mid-dating, or partnered — mirrors core.dating's state machine.
  App._loveLifeItems = function (s) {
    const age = (s.character && s.character.age) || 0;
    const minAge = 16;
    const dating = s.dating;
    const partner = (s.relationships || []).find(r => r.kind === "Partner" && r.alive);
    const incarcerated = s.crime && s.crime.is_incarcerated;

    if (incarcerated) {
      return [{
        icon: "lock", accent: "var(--c-bad)",
        title: "Romance — paused", subtitle: "You're inside. Nothing's happening on this front.",
        locked: true,
      }];
    }
    if (age < minAge) {
      return [{
        icon: "lock", accent: "var(--ink-faint)",
        title: "Too young", subtitle: `Dating opens at age ${minAge}.`,
        locked: true,
      }];
    }
    if (dating) {
      const chem = dating.chemistry || 0;
      const canCommit = chem >= 60;
      const chemColor = chem >= 66 ? "var(--c-good)"
                      : chem >= 33 ? "var(--c-warn)"
                      :              "var(--c-bad)";
      return [
        { icon: "heart", accent: "var(--c-looks)",
          title: `Dating ${dating.name}`,
          subtitle: `${dating.dates_been_on || 0} date${(dating.dates_been_on === 1) ? "" : "s"} so far.`,
          trailing: { kind: "meter", value: chem, color: chemColor } },
        { icon: "spark", accent: "var(--gold)",
          title: "Go on a date", subtitle: "Raises chemistry. Costs £50.",
          action: "go-on-date", trailing: { kind: "chevron" } },
        { icon: "heart", accent: canCommit ? "var(--gold)" : "var(--ink-faint)",
          title: canCommit ? "Become official" : "Become official — chemistry too low",
          subtitle: canCommit ? "Commit to this relationship." : "Need chemistry ≥ 60.",
          action: canCommit ? "become-official" : null,
          locked: !canCommit,
          trailing: canCommit ? { kind: "chevron" } : null },
        { icon: "x", accent: "var(--c-bad)",
          title: "End it", subtitle: "Stop seeing them.",
          action: "break-up", trailing: { kind: "chevron" } },
      ];
    }
    if (partner) {
      return [
        { icon: "heart", accent: "var(--c-looks)",
          title: `Together with ${partner.name}`,
          subtitle: "You're committed." },
        { icon: "x", accent: "var(--c-bad)",
          title: "Break up", subtitle: "End the relationship.",
          action: "break-up", trailing: { kind: "chevron" } },
      ];
    }
    return [
      { icon: "heart", accent: "var(--gold)",
        title: "Ask someone out", subtitle: "Start a new dating arc.",
        action: "ask-someone-out", trailing: { kind: "chevron" } },
    ];
  };
})(window.App = window.App || {});
