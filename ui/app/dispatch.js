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
      case "buy-car":             if (b.buyCar) await b.buyCar(payload); break;
      case "sell-car":            if (b.sellCar && typeof payload === "number") await b.sellCar(payload); break;
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
      case "try-for-baby":
        if (b.tryForBaby) await b.tryForBaby();
        break;
      case "name-baby": {
        // Read the user's name from the modal's text-input block, then
        // send it through nameBaby. Falls back to the suggested name if
        // they cleared the field.
        const input = document.querySelector('[data-modal-input="babyName"]');
        const raw = input ? input.value : "";
        const npcId = payload && payload.npc_id;
        if (b.nameBaby && typeof npcId === "number") {
          await b.nameBaby(npcId, raw);
        }
        break;
      }
      case "ask-someone-out":   if (b.askSomeoneOut) await b.askSomeoneOut(); break;
      case "go-on-date":        if (b.goOnDate) await b.goOnDate(); break;
      case "become-official":   if (b.becomeOfficial) await b.becomeOfficial(); break;
      case "break-up":          if (b.breakUp) await b.breakUp(); break;
      case "commit-crime":      if (b.commitCrime) await b.commitCrime(payload); break;
      case "ack-crime-outcome": if (b.acknowledgeCrimeOutcome) await b.acknowledgeCrimeOutcome(); break;
      case "save-game":
        if (b.save) await this.handleSaveLoad(b.save(), "Game saved");
        break;
      case "load-game":
        if (b.load) await this.handleSaveLoad(b.load(), "Game loaded");
        break;
      case "open-save-slot-actions":
        this.openSaveSlotActions(payload);
        break;
      case "save-to-slot":
        if (b.saveToSlot) {
          await this.handleSaveLoad(b.saveToSlot(payload), `Saved to slot ${payload}`);
          // Refresh the menu so the slot's metadata updates immediately.
          await this.openSaveLoadMenu();
        }
        break;
      case "load-from-slot":
        if (b.loadFromSlot) {
          await this.handleSaveLoad(b.loadFromSlot(payload), `Loaded slot ${payload}`);
        }
        break;
      case "delete-save-slot":
        if (b.deleteSaveSlot) {
          await this.handleSaveLoad(b.deleteSaveSlot(payload), `Slot ${payload} deleted`);
          await this.openSaveLoadMenu();
        }
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
    // Save-slot picker: one row per slot showing live metadata.
    // Tapping a row routes to an action picker (Save / Load / Delete).
    let slots = [];
    if (this.bridge && this.bridge.listSaveSlots) {
      try {
        const raw = await this.bridge.listSaveSlots();
        slots = typeof raw === "string" ? JSON.parse(raw) : raw;
      } catch (e) { slots = []; }
    }
    // Cache so the per-slot action submenu can render without a second bridge call.
    this._lastSlotsList = slots;

    const fmtRow = (slot) => {
      if (!slot.exists) {
        return {
          icon: "box", accent: "var(--ink-faint)",
          title: `Slot ${slot.slot_id}`, subtitle: "Empty",
          trailing: { kind: "chevron" },
          action: "open-save-slot-actions", payload: slot.slot_id,
        };
      }
      const money = (slot.money || 0).toLocaleString();
      const country = slot.country ? ` · ${slot.country}` : "";
      const when = slot.saved_at ? slot.saved_at.slice(0, 10) : "";
      const wherePart = when ? ` · ${when}` : "";
      return {
        icon: "save", accent: "var(--gold)",
        title: `${slot.character_name || "Unknown"}, age ${slot.age || 0}`,
        subtitle: `Slot ${slot.slot_id}${country} · £${money}${wherePart}`,
        trailing: { kind: "chevron" },
        action: "open-save-slot-actions", payload: slot.slot_id,
      };
    };

    LifeUI.modal({
      kind: "picker", title: "Save & Load", dismissable: true,
      blocks: [{ type: "list", items: slots.map(fmtRow) }],
      actions: [{ label: "Close", variant: "ghost", action: "__close" }],
    });
  };

  // Per-slot action picker (Save Here / Load / Delete).
  App.openSaveSlotActions = function (slotId) {
    const slots = this._lastSlotsList || [];
    const slot = slots.find(s => s.slot_id === slotId) || { exists: false, slot_id: slotId };

    const items = [
      { icon: "save", accent: "var(--gold)",
        title: slot.exists ? "Overwrite with current life" : "Save current life here",
        subtitle: slot.exists ? `Replaces ${slot.character_name || "the existing save"}` : "Write to this slot",
        trailing: { kind: "chevron" },
        action: "save-to-slot", payload: slotId },
    ];
    if (slot.exists) {
      items.push({
        icon: "box", accent: "var(--accent)",
        title: "Load this life",
        subtitle: `${slot.character_name || "Unknown"}, age ${slot.age || 0}`,
        trailing: { kind: "chevron" },
        action: "load-from-slot", payload: slotId,
      });
      items.push({
        icon: "x", accent: "var(--c-bad)",
        title: "Delete this save",
        subtitle: "Permanent. Can't be undone.",
        trailing: { kind: "chevron" },
        action: "delete-save-slot", payload: slotId,
      });
    }

    LifeUI.modal({
      kind: "picker", title: `Slot ${slotId}`, dismissable: true,
      blocks: [{ type: "list", items }],
      actions: [{ label: "Close", variant: "ghost", action: "__close" }],
    });
  };
})(window.App = window.App || {});
