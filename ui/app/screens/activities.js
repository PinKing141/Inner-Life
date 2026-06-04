/**
 * App.screens.activities — render the Activities tab.
 *
 * Lists everything in snapshot.activities. Locked rows show an
 * "Age N" badge; unlocked rows tap → do-activity. The accent token
 * is mapped from the descriptor's `accent` field to a CSS var.
 */
(function (App) {
  "use strict";

  App.renderActivities = function () {
    const s = this.state;
    const age = (s.character && s.character.age) || 0;
    const accent = {
      happy: "var(--c-happy)", health: "var(--c-health)",
      smarts: "var(--c-smarts)", looks: "var(--c-looks)",
    };
    const items = (s.activities || []).map(a => {
      const open = age >= (a.unlock || 0);
      return {
        icon: a.icon, accent: accent[a.accent] || "var(--gold)",
        title: a.title, subtitle: a.subtitle,
        locked: !open,
        action: open ? "do-activity" : null,
        payload: a.id,
        trailing: open ? { kind: "chevron" }
                       : { kind: "badge", text: "Age " + a.unlock, icon: "lock" },
      };
    });
    LifeUI.renderScreen("activities", [{ label: "Things To Do", items }]);
  };
})(window.App = window.App || {});
