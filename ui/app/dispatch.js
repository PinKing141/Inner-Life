/**
 * App.dispatch — the single action router. UI elements emit
 * { action, payload } via LifeUI's 'action' event; this maps each action
 * name to the right bridge slot (or local handler). Adding a UI verb
 * means adding one case here and one Slot in web_bridge.py.
 */
(function (App) {
  "use strict";

  App.dispatch = async function (action, payload) {
    const b = this.bridge;
    if (!b) return;
    switch (action) {
      case "do-activity":         await b.activity(payload); break;
      case "apply-for-job":       await b.applyForJob(payload); break;
      case "work-harder":         await b.workHarder(); break;
      case "request-raise":       await b.requestRaise(); break;
      case "request-promotion":   await b.requestPromotion(); break;
      case "quit-job":            await b.quitJob(); break;
      case "open-relation":       this.openRelationProfile(payload); break;
      case "rel-interact":
        await b.relationshipAction(payload.npc_id, payload.action);
        this.openRelationProfile(payload.npc_id);
        break;
      case "view-assets":         LifeUI.showScreen("assets"); break;
      case "view-listing":        this.openListingOptions(payload); break;
      case "buy-listing":         await b.buyHome(payload); break;
      case "mortgage-listing":    await b.buyHomeMortgage(payload); break;
      case "rent-listing":        await b.rentHome(payload); break;
      case "sell-home":           await b.sellHome(payload); break;
      case "stop-renting":        await b.stopRenting(); break;
      case "event-choice":        await b.choose(payload.choiceId); break;
      case "exam-answer":         await b.answerExam(payload.choiceId); break;
      case "exam-cheat":          await b.cheatExam(); break;
      case "ack-job-offer":       await b.acknowledgeJobOffer(); break;
      case "ack-promotion":       await b.acknowledgePromotion(); break;
      case "ack-job-loss":        await b.acknowledgeJobLoss(); break;
      case "ack-setback":         await b.acknowledgeCareerSetback(); break;
      case "clear-rejection":     await b.clearApplicationError(); break;
      case "ack-degree":          await b.acknowledgeDegree(); break;
      case "ack-milestone":       if (b.acknowledgeMilestone) await b.acknowledgeMilestone(); break;
      case "apply-university":    await b.applyUniversity(); break;
      case "uni-attend":          await b.setUniversityPlan(true, payload); break;
      case "uni-skip":            await b.setUniversityPlan(false, ""); break;
      case "drop-out-university": await b.dropOutUniversity(); break;
      case "enroll-postgrad":     await b.enrollPostgrad(payload); break;
      case "continue-as-heir":
        // Phase 5: crossing a generational boundary. Reset the latches
        // the death modal sets so the heir's life renders cleanly
        // (otherwise we'd suppress the next death modal because
        // deathShown stays true from the parent's death).
        this.deathShown = false;
        this.currentModalKey = null;
        this.loggedFeedCount = 0;
        if (b.continueAsHeir) await b.continueAsHeir(payload);
        break;
      case "save-game":
        if (b.save) await this.handleSaveLoad(b.save(), "Game saved");
        break;
      case "load-game":
        if (b.load) await this.handleSaveLoad(b.load(), "Game loaded");
        break;
    }
  };

  // Save/load round through an envelope { ok, error, snapshot } so the UI
  // can react to filesystem failures (permission denied, corrupt save)
  // with a toast rather than a silent crash or stale state.
  App.handleSaveLoad = async function (promise, successMsg) {
    try {
      const raw = await promise;
      const env = typeof raw === "string" ? JSON.parse(raw) : raw;
      if (env && env.snapshot) this.onSnapshot(env.snapshot);
      if (env && env.ok) {
        LifeUI.toast(successMsg);
      } else {
        LifeUI.toast((env && env.error) || "Operation failed");
      }
    } catch (e) {
      LifeUI.toast("Operation failed: " + (e && e.message ? e.message : e));
    }
  };

  App.openSaveLoadMenu = async function () {
    let hasSave = false;
    if (this.bridge && this.bridge.hasSave) {
      try { hasSave = await this.bridge.hasSave(); } catch (e) { hasSave = false; }
    }
    LifeUI.modal({
      kind: "picker", title: "Save & Load", dismissable: true,
      blocks: [{ type: "list", items: [
        { icon: "save", accent: "var(--gold)", title: "Save Game",
          subtitle: "Write the current life to disk",
          trailing: { kind: "chevron" }, action: "save-game" },
        { icon: "box", accent: hasSave ? "var(--ink-dim)" : "var(--ink-faint)",
          title: hasSave ? "Load Game" : "Load Game (no save found)",
          subtitle: hasSave ? "Restore a saved life" : "Save one first",
          trailing: { kind: "chevron" },
          action: hasSave ? "load-game" : null, locked: !hasSave },
      ] }],
      actions: [{ label: "Close", variant: "ghost", action: "__close" }],
    });
  };
})(window.App = window.App || {});
