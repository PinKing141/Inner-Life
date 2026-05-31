/**
 * App.bridge — Qt WebChannel hookup + browser-only MockBridge.
 *
 * In Qt, qwebchannel.js is loaded on demand from qrc:// and we wire the
 * `bridge` and `windowControls` exported objects to App. In a plain
 * browser (no Qt), the MockBridge serves a canonical recorded snapshot
 * and every verb is inert — useful for visual development without
 * launching the desktop shell.
 */
(function (App) {
  "use strict";

  App.ensureQtWebChannel = async function () {
    if (typeof qt === "undefined" || typeof QWebChannel !== "undefined") return;
    await new Promise((resolve, reject) => {
      const s = document.createElement("script");
      s.src = "qrc:///qtwebchannel/qwebchannel.js";
      s.onload = resolve;
      s.onerror = () => reject(new Error("qtwebchannel.js failed to load"));
      document.head.appendChild(s);
    });
  };

  App.connect = async function () {
    await this.ensureQtWebChannel();
    if (typeof QWebChannel !== "undefined" && typeof qt !== "undefined") {
      await new Promise((resolve) => {
        new QWebChannel(qt.webChannelTransport, (channel) => {
          this.bridge = channel.objects.bridge;
          this.windowControls = channel.objects.windowControls || null;
          this.bridge.stateChanged.connect((json) => this.onSnapshot(JSON.parse(json)));
          resolve();
        });
      });
      const initial = await this.bridge.snapshot();
      this.onSnapshot(JSON.parse(initial));
    } else {
      console.warn("QWebChannel not present; using mock bridge.");
      this.bridge = MockBridge.make((s) => this.onSnapshot(s));
      this.onSnapshot(MockBridge.initial());
    }
    this.wireWindowControls();
  };

  // Wires the topbar's window control buttons (min/max/close) + drag to
  // the Qt-side WindowControls slots. Safe to call when windowControls is
  // null — the buttons simply do nothing in browser preview.
  App.wireWindowControls = function () {
    const wc = this.windowControls;
    document.querySelectorAll(".win-btn").forEach((btn) => {
      const action = btn.dataset.win;
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        if (!wc) return;
        if (action === "min" && wc.minimize) wc.minimize();
        else if (action === "max" && wc.toggleMaximize) wc.toggleMaximize();
        else if (action === "close" && wc.closeWindow) wc.closeWindow();
      });
    });
    const bar = document.querySelector(".app-topbar[data-drag]");
    if (bar && wc && wc.startDrag) {
      bar.addEventListener("mousedown", (e) => {
        if (e.target.closest("button")) return;
        wc.startDrag();
      });
    }
  };

  // ===== MockBridge (browser-only preview; zero simulation) =====

  const MockBridge = (() => {
    const CREATION = (typeof window !== "undefined" && window.MOCK_SNAPSHOT_CREATION)
      || { mode: "CREATION", countries: [] };
    const PLAYING = (typeof window !== "undefined" && window.MOCK_SNAPSHOT_PLAYING) || null;
    let state = CREATION;
    let pushTo = null;
    const INERT = [
      "ageUp", "choose", "applyForJob", "activity", "workHarder", "requestRaise",
      "requestPromotion", "quitJob", "relationshipAction", "buyHome",
      "buyHomeMortgage", "rentHome", "sellHome", "stopRenting",
      "setUniversityPlan", "acknowledgeDegree", "dropOutUniversity",
      "answerExam", "cheatExam", "applyUniversity", "enrollPostgrad",
      "acknowledgeJobOffer", "acknowledgePromotion", "acknowledgeJobLoss",
      "acknowledgeCareerSetback", "clearApplicationError",
    ];
    return {
      initial() { return CREATION; },
      make(onChange) {
        pushTo = onChange;
        const api = {
          async snapshot() { return JSON.stringify(state); },
          async hasSave() { return false; },
          async newGame() { return api.newGameFull(); },
          async newGameFull() {
            if (PLAYING) state = PLAYING;
            if (pushTo) pushTo(state);
            return JSON.stringify(state);
          },
          // Save/load go through the envelope path; mock them so the
          // toast UX is exercisable in browser preview too.
          async save() {
            return JSON.stringify({ ok: false, error: "Browser preview cannot save.", snapshot: state });
          },
          async load() {
            return JSON.stringify({ ok: false, error: "No save in browser preview.", snapshot: state });
          },
        };
        for (const verb of INERT) {
          api[verb] = async () => {
            console.warn(`MockBridge: '${verb}' is inert in browser preview.`);
            if (pushTo) pushTo(state);
            return JSON.stringify(state);
          };
        }
        return api;
      },
    };
  })();
  App.MockBridge = MockBridge;
})(window.App = window.App || {});
