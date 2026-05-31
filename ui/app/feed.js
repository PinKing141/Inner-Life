/**
 * App.feed — annual life-log: every new entry on the snapshot's feed list
 * gets a category (for the timeline's coloured dot) and is appended to the
 * Life screen. loggedFeedCount tracks how many we've already drawn so we
 * never duplicate on re-render.
 */
(function (App) {
  "use strict";

  App.appendNewFeedEntries = function () {
    const feed = this.state.feed || [];
    for (let i = this.loggedFeedCount; i < feed.length; i++) {
      const f = feed[i];
      LifeUI.logEvent({
        age: f.age,
        category: this.categoryFor(f),
        text: f.text || "",
      });
    }
    this.loggedFeedCount = feed.length;
  };

  App.categoryFor = function (entry) {
    const id = (entry.entry_id || "").toLowerCase();
    const kind = entry.kind || "neutral";
    if (id.includes("birth")) return "birth";
    if (id.includes("death") || id.includes("agent_death")) return "family";
    if (id.startsWith("feed:edu") || id.startsWith("feed:postgrad") || id.startsWith("feed:exam")) return "education";
    if (id.startsWith("feed:job") || id.startsWith("feed:raise") || id.startsWith("feed:promo") ||
        id.startsWith("feed:quit") || id.startsWith("feed:work")) return "money";
    if (id.startsWith("feed:buy_home") || id.startsWith("feed:rent_home") ||
        id.startsWith("feed:sell_home") || id.startsWith("feed:mortgage") ||
        id.startsWith("feed:stop_rent")) return "money";
    if (id.startsWith("feed:help") || id.startsWith("feed:rel:")) return "social";
    if (id.startsWith("feed:annual")) return "event";
    if (kind === "good") return "milestone";
    if (kind === "bad") return "health";
    return "event";
  };
})(window.App = window.App || {});
