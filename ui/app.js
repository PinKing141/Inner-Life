/**
 * App — the seam between the Qt bridge (Python core) and LifeUI.
 *
 * Snapshot in, LifeUI calls out. JS holds no game state and runs no rules.
 * Each stateChanged triggers render(), which delegates to the per-tab
 * screen renderers under app/screens/, the feed appender (app/feed.js),
 * and the modal coordinator under app/modals/. Save/load and bridge
 * connection live in app/bridge.js and app/dispatch.js.
 *
 * Character creation is gone — the controller auto-spawns a random baby
 * in a random country on boot. The snapshot lands straight in PLAYING.
 */

window.App = window.App || {};
Object.assign(window.App, {
  bridge: null,
  windowControls: null,  // Qt-only; null in browser preview
  state: null,
  loggedFeedCount: 0,
  currentModalKey: null,
  deathShown: false,

  // ===== Snapshot entry point =====

  onSnapshot(snap) {
    const prevMode = this.state ? this.state.mode : null;
    this.state = snap;
    this.applySettingsToDOM(snap.settings);
    if (prevMode !== "PLAYING" && prevMode !== "DEATH") {
      LifeUI.scene("game");
      LifeUI.clearLife();
      this.loggedFeedCount = 0;
      this.currentModalKey = null;
      this.deathShown = false;
    }
    this.render();
  },

  // ===== Render: snapshot -> LifeUI =====

  render() {
    const s = this.state;
    if (!s || (s.mode !== "PLAYING" && s.mode !== "DEATH")) return;
    const ch = s.character || {};
    const country = (s.countries || []).find(c => c.name === ch.country) || {};
    const flag = country.flag_svg ? this.imgTag(country.flag_svg) : "";
    // Identity-area "stage" keeps its nuanced label (Toddler / Teen /
    // Mature Adult). The Occupation tab is always labelled "Occupation"
    // but goes greyed when the player is too young to use it.
    LifeUI.setIdentity({
      name: ch.name || "—",
      flag,
      stage: s.career ? s.career.title : this.stageFor(ch.age || 0, s.education),
      stageIcon: this.stageIconFor(ch.age || 0, s.education, !!s.career),
      occupationLocked: this.occupationLocked(s),
      age: ch.age || 0,
      location: ch.city ? `${ch.city}, ${ch.country}` : (ch.country || "—"),
      balance: s.money || 0,
    });
    LifeUI.setStats(s.stats || {});
    this.renderActivities();
    this.renderOccupation();
    this.renderRelations();
    this.renderAssets();
    this.renderCrime();
    this.appendNewFeedEntries();
    this.syncModal();
  },
});

// ===== LifeUI event wiring =====

LifeUI.on("ageup", () => { if (App.bridge) App.bridge.ageUp(); });

LifeUI.on("action", ({ action, payload }) => App.dispatch(action, payload));

LifeUI.on("menu", () => App.openMenu());

// Apply Settings v1 display flags to <html> so CSS attribute selectors
// react. Idempotent — safe to call on every snapshot.
App.applySettingsToDOM = function (settings) {
  if (!settings) return;
  const html = document.documentElement;
  if (settings.font_size) html.setAttribute("data-font-size", settings.font_size);
  html.toggleAttribute("data-reduced-motion", !!settings.reduced_motion);
  html.toggleAttribute("data-high-contrast", !!settings.high_contrast);
};

// ===== Bootstrap =====

document.addEventListener("DOMContentLoaded", () => {
  // Configure 5 screens BEFORE mount: first 4 appear in the nav (life /
  // activities / career / relations), assets is the 5th and is reached
  // via a "Property & Assets" list-item on the Career screen.
  LifeUI.registerScreen("life",       { label: "Life",       icon: "infant" });
  LifeUI.registerScreen("activities", { label: "Activities", icon: "dots"   });
  LifeUI.registerScreen("career",     { label: "Career",     icon: "brief"  });
  LifeUI.registerScreen("relations",  { label: "Relations",  icon: "heart"  });
  LifeUI.registerScreen("assets",     { label: "Assets",     icon: "assets" });
  LifeUI.mount("#game");
  App.connect();
});
