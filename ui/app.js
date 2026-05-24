/**
 * App — the seam between the Qt bridge (Python core) and LifeUI.
 *
 * Pattern: snapshot -> translation -> LifeUI calls. The JS holds no game
 * state and runs no rules. On each stateChanged we:
 *   - setIdentity / setStats from the snapshot,
 *   - render each screen from snapshot lists,
 *   - append any new feed entries,
 *   - raise (or close) the modal for whichever pending_* field is set.
 *
 * Creation is a pure UI flow: JS walks the 4 steps, then issues a single
 * newGameFull() bridge call. After that the engine drives.
 *
 * Browser-only preview (no Qt): MockBridge serves a canonical recorded
 * snapshot; every verb is inert. The laws live in Python alone.
 */

const App = {
  bridge: null,
  windowControls: null,  // Qt-only; null in browser preview
  state: null,
  loggedFeedCount: 0,
  currentModalKey: null,
  deathShown: false,
  creation: { first_name: "", last_name: "", gender: "", country: "", city: "", talent: "" },

  // ===== Connection =====

  async ensureQtWebChannel() {
    if (typeof qt === "undefined" || typeof QWebChannel !== "undefined") return;
    await new Promise((resolve, reject) => {
      const s = document.createElement("script");
      s.src = "qrc:///qtwebchannel/qwebchannel.js";
      s.onload = resolve;
      s.onerror = () => reject(new Error("qtwebchannel.js failed to load"));
      document.head.appendChild(s);
    });
  },

  async connect() {
    await this.ensureQtWebChannel();
    if (typeof QWebChannel !== "undefined" && typeof qt !== "undefined") {
      await new Promise((resolve) => {
        new QWebChannel(qt.webChannelTransport, (channel) => {
          this.bridge = channel.objects.bridge;
          // Frameless-window controls are optional — only present when the Qt
          // shell exposes them. Browser preview leaves this null.
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
  },

  // Wires the topbar's window control buttons (min/max/close) + drag to the
  // Qt-side WindowControls slots. Safe to call when windowControls is null —
  // the buttons simply do nothing in browser preview.
  wireWindowControls() {
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
    // Drag the window by pressing the topbar (excluding buttons).
    const bar = document.querySelector(".app-topbar[data-drag]");
    if (bar && wc && wc.startDrag) {
      bar.addEventListener("mousedown", (e) => {
        if (e.target.closest("button")) return;
        wc.startDrag();
      });
    }
  },

  // ===== Snapshot entry point =====

  onSnapshot(snap) {
    const prevMode = this.state ? this.state.mode : null;
    this.state = snap;
    if (snap.mode === "CREATION") {
      if (prevMode !== "CREATION") this.startCreation();
      return;
    }
    if (prevMode !== "PLAYING" && prevMode !== "DEATH") {
      // Transitioned into the game from creation.
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
    const flag = country.flag_svg ? imgTag(country.flag_svg) : "";
    LifeUI.setIdentity({
      name: ch.name || "—",
      flag,
      stage: s.career ? s.career.title : this.stageFor(ch.age || 0, s.education),
      location: ch.city ? `${ch.city}, ${ch.country}` : (ch.country || "—"),
      balance: s.money || 0,
    });
    LifeUI.setStats(s.stats || {});
    this.renderActivities();
    this.renderCareer();
    this.renderRelations();
    this.renderAssets();
    this.appendNewFeedEntries();
    this.syncModal();
  },

  stageFor(age, edu) {
    if (edu && edu.in_school) return edu.level === "University" ? "University" : "School";
    if (age < 2) return "Infant";
    if (age < 5) return "Toddler";
    if (age < 13) return "Child";
    if (age < 18) return "Teenager";
    if (age < 30) return "Young Adult";
    if (age < 55) return "Adult";
    if (age < 70) return "Mature Adult";
    return "Senior";
  },

  // ===== Screens =====

  renderActivities() {
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
  },

  renderCareer() {
    const s = this.state;
    const job = s.career;
    const groups = [];

    if (job) {
      groups.push({
        label: "Current Job",
        items: [{
          icon: "brief", accent: "var(--gold)",
          title: job.title,
          subtitle: `${job.employer || "Employer"} · £${(job.salary || 0).toLocaleString()}/yr · Performance ${job.performance}`,
        }],
      });
      groups.push({
        label: "Career Actions",
        items: [
          { icon: "spark", accent: "var(--c-happy)", title: "Work Harder",
            subtitle: "Push for performance; costs a little happiness",
            trailing: { kind: "chevron" }, action: "work-harder" },
          { icon: "gem", accent: "var(--cat-money)", title: "Ask for a Raise",
            subtitle: "Pitch a salary bump",
            trailing: { kind: "chevron" }, action: "request-raise" },
          { icon: "trophy", accent: "var(--gold)", title: "Ask for Promotion",
            subtitle: "Aim for the next rung",
            trailing: { kind: "chevron" }, action: "request-promotion" },
          { icon: "x", accent: "var(--c-bad)", title: "Quit Job",
            subtitle: "Walk away from this role",
            trailing: { kind: "chevron" }, action: "quit-job" },
        ],
      });
    } else {
      groups.push({
        label: "Current Job",
        emptyText: "You are unemployed. Browse jobs below.",
        items: [],
      });
    }

    // Available jobs the player meets the requirements for.
    const age = (s.character && s.character.age) || 0;
    const smarts = (s.stats && s.stats.smarts) || 0;
    const edu = s.education || {};
    const meetsEducation = (need) => {
      const order = ["None", "Primary School", "Secondary School", "Secondary Education", "University"];
      return order.indexOf(edu.level || "None") >= order.indexOf(need);
    };
    const jobs = (s.jobs || []).filter(j => {
      if (age < j.min_age) return false;
      if (smarts < j.min_smarts) return false;
      if (!meetsEducation(j.min_education)) return false;
      if (j.required_field && (!edu.degree_completed || edu.degree_field !== j.required_field)) return false;
      return true;
    });
    groups.push({
      label: "Available Jobs",
      emptyText: "No jobs you qualify for. Study to unlock more.",
      items: jobs.map(j => ({
        icon: "brief", accent: "var(--cat-money)",
        title: j.title,
        subtitle: `${j.employer || ""} · £${(j.salary || 0).toLocaleString()}/yr`,
        trailing: { kind: "chevron" },
        action: "apply-for-job", payload: j.job_id,
      })),
    });

    // Education actions when relevant.
    if (!edu.in_school && edu.degree_completed && !edu.masters_completed) {
      groups.push({
        label: "Further Study",
        items: [{
          icon: "cap", accent: "var(--cat-education)",
          title: "Enrol in a Master's Degree",
          subtitle: "Deepen your field; two years.",
          trailing: { kind: "chevron" },
          action: "enroll-postgrad", payload: "Master's Degree",
        }],
      });
    } else if (!edu.in_school && edu.masters_completed && !edu.doctorate_completed) {
      groups.push({
        label: "Further Study",
        items: [{
          icon: "cap", accent: "var(--cat-education)",
          title: "Enrol in a Doctorate",
          subtitle: "Three or more years of research.",
          trailing: { kind: "chevron" },
          action: "enroll-postgrad", payload: "Doctorate",
        }],
      });
    } else if (!edu.in_school && !edu.degree_completed && age >= 18) {
      groups.push({
        label: "Further Study",
        items: [{
          icon: "cap", accent: "var(--cat-education)",
          title: "Apply to University",
          subtitle: "Open a course picker",
          trailing: { kind: "chevron" },
          action: "apply-university",
        }],
      });
    }
    if (edu.in_school && edu.level === "University") {
      groups.push({
        label: "Currently Studying",
        items: [{
          icon: "cap", accent: "var(--cat-education)",
          title: `${edu.university_name || "University"} — ${edu.university_major || "Undeclared"}`,
          subtitle: `${edu.study_years_left || 0} years remaining`,
        }, {
          icon: "x", accent: "var(--c-bad)", title: "Drop Out",
          subtitle: "Leave university without a degree",
          trailing: { kind: "chevron" },
          action: "drop-out-university",
        }],
      });
    }

    // Gateway into the Assets screen.
    groups.push({
      label: "Wealth",
      items: [{
        icon: "house", accent: "var(--gold)",
        title: "Property & Assets",
        subtitle: `Net worth £${(s.net_worth || 0).toLocaleString()}`,
        trailing: { kind: "chevron" },
        action: "view-assets",
      }],
    });

    LifeUI.renderScreen("career", groups);
  },

  renderRelations() {
    const s = this.state;
    const all = s.relationships || [];
    const partner = all.filter(r => r.kind === "Partner");
    const family = all.filter(r => ["Mother", "Father", "Sibling"].includes(r.kind));
    const friends = all.filter(r => ["Friend", "Coworker"].includes(r.kind));
    const mk = (r) => ({
      icon: r.kind === "Partner" ? "heart" : "person",
      accent: r.alive
        ? (r.kind === "Partner" ? "var(--c-looks)" : "var(--cat-family)")
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
      { label: "Partner", emptyText: "No partner yet.", items: partner.map(mk) },
      { label: "Family", emptyText: "No family on record.", items: family.map(mk) },
      { label: "Friends & Coworkers", emptyText: "No close ties yet.", items: friends.map(mk) },
    ]);
  },

  renderAssets() {
    const s = this.state;
    const props = s.properties || [];
    const market = s.housing_market || [];
    const rental = s.rental;
    const groups = [];

    groups.push({
      label: "Property",
      emptyText: "You own no property.",
      items: props.map(p => ({
        icon: "house", accent: "var(--gold)",
        title: p.name,
        subtitle: p.mortgage_balance
          ? `Value £${(p.value || 0).toLocaleString()} · Mortgage £${p.mortgage_balance.toLocaleString()}`
          : `Value £${(p.value || 0).toLocaleString()}`,
        trailing: { kind: "value", text: "£" + (p.value || 0).toLocaleString() },
        action: "sell-home", payload: p.id,
      })),
    });

    if (rental) {
      groups.push({
        label: "Renting",
        items: [{
          icon: "house", accent: "var(--cat-money)",
          title: rental.name,
          subtitle: `Rent £${(rental.rent || 0).toLocaleString()}/yr`,
          trailing: { kind: "chevron" },
          action: "stop-renting",
        }],
      });
    }

    groups.push({
      label: "Housing Market",
      emptyText: "No listings in your city right now.",
      items: market.map(m => ({
        icon: "house", accent: "var(--cat-money)",
        title: m.name,
        subtitle: `Buy £${(m.price || 0).toLocaleString()} · Rent £${(m.rent || 0).toLocaleString()}/yr`,
        trailing: { kind: "chevron" },
        action: "view-listing", payload: m.id,
      })),
    });

    LifeUI.renderScreen("assets", groups);
  },

  // ===== Feed =====

  appendNewFeedEntries() {
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
  },

  categoryFor(entry) {
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
  },

  // ===== Modal coordination =====

  syncModal() {
    const key = this.computeModalKey(this.state);
    if (key === this.currentModalKey) return;
    this.currentModalKey = key;
    if (key === null) { LifeUI.closeModal(); return; }
    this.raiseModalFor(key, this.state);
  },

  computeModalKey(s) {
    if (s.pending_event && s.pending_event_id) return "event:" + s.pending_event_id + ":" + s.tick;
    if (s.pending_job_offer) return "offer:" + (s.pending_job_offer.title || "") + ":" + s.tick;
    if (s.pending_promotion) return "promo:" + (s.pending_promotion.title || "") + ":" + s.tick;
    if (s.pending_job_loss) return "loss:" + (s.pending_job_loss.title || "") + ":" + s.tick;
    if (s.pending_career_setback) return "setback:" + (s.pending_career_setback.type || "") + ":" + s.tick;
    if (s.job_application_error) return "reject:" + s.tick + ":" + (s.job_application_error || "").slice(0, 24);
    if (s.exam && s.exam.current && !s.exam.finished) return "exam:" + s.exam.index;
    if (s.education && s.education.degree_award_pending) return "degree:" + s.tick;
    if (s.education && s.education.awaiting_university_choice) return "uni:" + s.tick;
    if (s.mode === "DEATH" && !this.deathShown) { this.deathShown = true; return "death"; }
    return null;
  },

  raiseModalFor(key, s) {
    if (key.startsWith("event:"))   this.raiseEventModal(s.pending_event);
    else if (key.startsWith("offer:"))   this.raiseJobOfferModal(s.pending_job_offer);
    else if (key.startsWith("promo:"))   this.raisePromotionModal(s.pending_promotion);
    else if (key.startsWith("loss:"))    this.raiseJobLossModal(s.pending_job_loss);
    else if (key.startsWith("setback:")) this.raiseSetbackModal(s.pending_career_setback);
    else if (key.startsWith("reject:"))  this.raiseRejectionModal(s.job_application_error);
    else if (key.startsWith("exam:"))    this.raiseExamModal(s.exam);
    else if (key.startsWith("degree:"))  this.raiseDegreeModal(s.education);
    else if (key.startsWith("uni:"))     this.raiseUniversityModal(s);
    else if (key === "death")            this.raiseDeathModal(s);
  },

  raiseEventModal(ev) {
    LifeUI.modal({
      kind: "event", title: ev.title || "A Decision",
      blocks: [
        { type: "text", text: ev.text || "" },
        { type: "choices", action: "event-choice",
          choices: (ev.choices || []).map((c, i) => ({ id: i, label: c.text || "" })) },
      ],
    });
  },

  raiseJobOfferModal(o) {
    LifeUI.modal({
      kind: "offer",
      title: `${o.title}${o.employer ? " — " + o.employer : ""}`,
      blocks: [
        { type: "text", text: `You were offered a position as a ${o.title}.` },
        { type: "deltas", deltas: [
          { label: "Salary", value: `£${(o.salary || 0).toLocaleString()} / yr`, tone: "good" },
        ] },
      ],
      actions: [{ label: "Acknowledge", variant: "primary", action: "ack-job-offer" }],
    });
  },

  raisePromotionModal(p) {
    LifeUI.modal({
      kind: "award", title: "Promoted",
      blocks: [{ type: "award", icon: "trophy", title: p.title,
        subtitle: `${p.employer || ""} · £${(p.salary || 0).toLocaleString()} (+${p.pct}%)` }],
      actions: [{ label: "Excellent", variant: "primary", action: "ack-promotion" }],
    });
  },

  raiseJobLossModal(l) {
    LifeUI.modal({
      kind: "notice",
      title: l.fired ? "You Were Fired" : "You Were Laid Off",
      blocks: [{ type: "text", text:
        `You lost your position as ${l.title} at ${l.employer || "your employer"} — ${l.reason || "let go"}.` }],
      actions: [{ label: "Acknowledge", variant: "ghost", action: "ack-job-loss" }],
    });
  },

  raiseSetbackModal(c) {
    LifeUI.modal({
      kind: "notice",
      title: c.type === "demotion" ? "Demoted" : "Pay Cut",
      blocks: [{ type: "text", text:
        c.type === "demotion"
          ? `You were demoted to ${c.title} (−${c.pct}%).`
          : `Your salary was cut by ${c.pct}% (${c.reason || ""}).` }],
      actions: [{ label: "Acknowledge", variant: "ghost", action: "ack-setback" }],
    });
  },

  raiseRejectionModal(msg) {
    LifeUI.modal({
      kind: "notice", title: "Application Rejected", dismissable: true,
      blocks: [{ type: "text", text: msg || "" }],
      actions: [{ label: "Close", variant: "ghost", action: "clear-rejection" }],
    });
  },

  raiseExamModal(exam) {
    const q = exam.current;
    const revealed = exam.revealed != null ? exam.revealed : null;
    const opts = (q.options || []).map((opt, i) => ({
      id: i, label: opt + (revealed === i ? "  ✓" : ""),
    }));
    LifeUI.modal({
      kind: "exam", title: `Question ${exam.index + 1} of ${exam.total}`,
      blocks: [
        q.subject ? { type: "text", text: `<b>${q.subject}</b>` } : null,
        { type: "text", text: q.prompt || "" },
        { type: "choices", action: "exam-answer", choices: opts },
      ].filter(Boolean),
      actions: [{ label: "Cheat", variant: "danger", action: "exam-cheat", keepOpen: true }],
    });
  },

  raiseDegreeModal(edu) {
    LifeUI.modal({
      kind: "award", title: "Degree Awarded",
      blocks: [{ type: "award", icon: "cap",
        title: edu.degree_award_label || "Degree",
        subtitle: `Congratulations on completing your studies at ${edu.university_name || "your university"}.` }],
      actions: [{ label: "Wonderful", variant: "primary", action: "ack-degree" }],
    });
  },

  raiseUniversityModal(s) {
    const courses = s.courses || [];
    const tier = (s.education && s.education.admitted_tier) || "Community";
    LifeUI.modal({
      kind: "picker", title: "Choose Your Course", dismissable: true,
      eyebrow: `Admitted: ${tier}`,
      blocks: [{ type: "list", items:
        courses.map(c => ({
          icon: "cap", accent: "var(--cat-education)",
          title: c.major, subtitle: `Field: ${c.field}`,
          trailing: { kind: "chevron" },
          action: "uni-attend", payload: c.major,
        })).concat([{
          icon: "x", accent: "var(--c-bad)",
          title: "Skip University", subtitle: "Take a different path",
          trailing: { kind: "chevron" }, action: "uni-skip",
        }]) }],
    });
  },

  raiseDeathModal(s) {
    const ch = s.character || {};
    LifeUI.modal({
      kind: "award", title: "End of Life", dismissable: true,
      blocks: [{ type: "award", icon: "hourglass",
        title: `${ch.name || "You"} died at ${ch.age || 0}`,
        subtitle: "Your story is complete. Open the menu to start another life." }],
      actions: [{ label: "Close", variant: "ghost", action: "__close" }],
    });
  },

  // ===== Save / load =====

  async openSaveLoadMenu() {
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
  },

  // ===== Relationship profile (modal with keepOpen interactions) =====

  openRelationProfile(npcId) {
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
          { type: "section", label: "Interactions" },
          { type: "list", items: [
            { icon: "heart", accent: "var(--c-good)", title: "Talk", subtitle: "A nice chat",
              trailing: { kind: "chevron" }, action: "rel-interact",
              payload: { npc_id: npcId, action: "talk" } },
            { icon: "spark", accent: "var(--c-happy)", title: "Compliment",
              subtitle: "A small lift", trailing: { kind: "chevron" },
              action: "rel-interact", payload: { npc_id: npcId, action: "compliment" } },
            { icon: "gem", accent: "var(--gold)", title: "Give a Gift",
              subtitle: "Costs £50", trailing: { kind: "chevron" },
              action: "rel-interact", payload: { npc_id: npcId, action: "gift" } },
            { icon: "x", accent: "var(--c-bad)", title: "Argue",
              subtitle: "It will cost you", trailing: { kind: "chevron" },
              action: "rel-interact", payload: { npc_id: npcId, action: "argue" } },
          ] },
        ] : []),
      ],
      actions: [{ label: "Close", variant: "ghost", action: "__close" }],
    });
  },

  openListingOptions(listingId) {
    const m = (this.state.housing_market || []).find(x => x.id === listingId);
    if (!m) return;
    LifeUI.modal({
      kind: "picker", title: m.name, dismissable: true,
      blocks: [
        { type: "text", text:
          `Price £${(m.price || 0).toLocaleString()} · Annual rent £${(m.rent || 0).toLocaleString()}` },
        { type: "list", items: [
          { icon: "gem", accent: "var(--gold)", title: "Buy Outright",
            subtitle: `£${(m.price || 0).toLocaleString()} now`,
            trailing: { kind: "chevron" }, action: "buy-listing", payload: listingId },
          { icon: "house", accent: "var(--cat-money)", title: "Buy with Mortgage",
            subtitle: "10% deposit, 25-year term",
            trailing: { kind: "chevron" }, action: "mortgage-listing", payload: listingId },
          { icon: "house", accent: "var(--c-smarts)", title: "Rent",
            subtitle: `£${(m.rent || 0).toLocaleString()}/yr`,
            trailing: { kind: "chevron" }, action: "rent-listing", payload: listingId },
        ] },
      ],
      actions: [{ label: "Close", variant: "ghost", action: "__close" }],
    });
  },

  // ===== Creation flow =====

  startCreation() {
    this.creation = { first_name: "", last_name: "", gender: "", country: "", city: "", talent: "" };
    LifeUI.creationShow({
      id: "identity", step: 1, total: 4,
      title: "Who Are You?",
      subtitle: "Every life begins with a name.",
      fields: [
        { type: "text", key: "first_name", label: "First Name", placeholder: "e.g. Dini" },
        { type: "text", key: "last_name", label: "Last Name", placeholder: "e.g. Elyas" },
        { type: "segment", key: "gender", label: "Gender",
          options: [{ id: "Male", label: "Male" }, { id: "Female", label: "Female" }, { id: "NonBinary", label: "Non-Binary" }] },
      ],
    });
  },

  creationStep(stepId, prefill) {
    const countries = (this.state && this.state.countries) || [];
    if (stepId === "identity") {
      LifeUI.creationShow({
        id: "identity", step: 1, total: 4,
        title: "Who Are You?",
        subtitle: "Every life begins with a name.",
        fields: [
          { type: "text", key: "first_name", label: "First Name",
            placeholder: "e.g. Dini", value: this.creation.first_name },
          { type: "text", key: "last_name", label: "Last Name",
            placeholder: "e.g. Elyas", value: this.creation.last_name },
          { type: "segment", key: "gender", label: "Gender",
            value: this.creation.gender,
            options: [{ id: "Male", label: "Male" }, { id: "Female", label: "Female" }, { id: "NonBinary", label: "Non-Binary" }] },
        ],
      });
    } else if (stepId === "origin") {
      LifeUI.creationShow({
        id: "origin", step: 2, total: 4, back: true,
        title: "Where Were You Born?",
        fields: [{
          type: "flaggrid", key: "country", label: "Country",
          value: prefill != null ? prefill : this.creation.country,
          options: countries.map(c => ({
            id: c.code, label: c.name, flag: imgTag(c.flag_svg),
          })),
        }],
      });
    } else if (stepId === "city") {
      const c = countries.find(x => x.code === this.creation.country) || { cities: [], name: "" };
      LifeUI.creationShow({
        id: "city", step: 3, total: 4, back: true,
        title: "Your Hometown",
        subtitle: `Cities of ${c.name || ""}.`,
        fields: [{
          type: "list", key: "city", label: "City",
          value: prefill != null ? prefill : this.creation.city,
          options: (c.cities || []).map(name => ({ id: name, label: name })),
        }],
      });
    } else if (stepId === "talent") {
      LifeUI.creationShow({
        id: "talent", step: 4, total: 4, back: true, submitLabel: "Begin Life",
        title: "A Natural Gift",
        subtitle: "One thing you were born good at.",
        fields: [{
          type: "cards", key: "talent", label: "Talent",
          value: prefill != null ? prefill : this.creation.talent,
          options: [
            { id: "Academics", label: "Academics", icon: "smarts", accent: "var(--c-smarts)",
              desc: "Smarts climb faster — and unlock the highest-paid careers." },
            { id: "Acting", label: "Acting", icon: "looks", accent: "var(--c-looks)",
              desc: "Looks and social magnetism come easily." },
            { id: "Sports", label: "Sports", icon: "health", accent: "var(--c-health)",
              desc: "Strong health from birth; you age slower." },
          ],
        }],
      });
    }
  },

  // ===== Action router =====

  async dispatch(action, payload) {
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
      case "apply-university":    await b.applyUniversity(); break;
      case "uni-attend":          await b.setUniversityPlan(true, payload); break;
      case "uni-skip":            await b.setUniversityPlan(false, ""); break;
      case "drop-out-university": await b.dropOutUniversity(); break;
      case "enroll-postgrad":     await b.enrollPostgrad(payload); break;
      case "save-game":
        if (b.save) { await b.save(); LifeUI.toast("Game saved"); }
        break;
      case "load-game":
        if (b.load) { await b.load(); LifeUI.toast("Game loaded"); }
        break;
    }
  },
};

function imgTag(src) {
  return `<img src="${src}" alt="" style="display:block;width:100%;height:100%;object-fit:cover">`;
}

// ===== LifeUI event wiring =====

LifeUI.on("ageup", () => { if (App.bridge) App.bridge.ageUp(); });

LifeUI.on("action", ({ action, payload }) => App.dispatch(action, payload));

LifeUI.on("menu", () => App.openSaveLoadMenu());

LifeUI.on("creation-submit", ({ stepId, values }) => {
  Object.assign(App.creation, values);
  if (stepId === "identity")     App.creationStep("origin");
  else if (stepId === "origin")  App.creationStep("city");
  else if (stepId === "city")    App.creationStep("talent");
  else if (stepId === "talent") {
    const c = App.creation;
    LifeUI.scene("game");
    LifeUI.clearLife();
    App.loggedFeedCount = 0;
    App.currentModalKey = null;
    App.deathShown = false;
    if (App.bridge.newGameFull) {
      App.bridge.newGameFull(c.first_name, c.last_name, c.gender, c.country, c.city, c.talent);
    } else {
      App.bridge.newGame(`${c.first_name} ${c.last_name}`.trim(), c.gender, c.country, c.talent);
    }
  }
});

LifeUI.on("creation-back", ({ stepId }) => {
  if (stepId === "origin")    App.creationStep("identity");
  else if (stepId === "city")   App.creationStep("origin", App.creation.country);
  else if (stepId === "talent") App.creationStep("city", App.creation.city);
});

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
    "save", "load",
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

// ===== Bootstrap =====

document.addEventListener("DOMContentLoaded", () => {
  // Configure 5 screens BEFORE mount: first 4 appear in the nav (life /
  // activities / career / relations), assets is the 5th and is reached via
  // a "Property & Assets" list-item on the Career screen.
  LifeUI.registerScreen("life",       { label: "Life",       icon: "infant" });
  LifeUI.registerScreen("activities", { label: "Activities", icon: "dots"   });
  LifeUI.registerScreen("career",     { label: "Career",     icon: "brief"  });
  LifeUI.registerScreen("relations",  { label: "Relations",  icon: "heart"  });
  LifeUI.registerScreen("assets",     { label: "Assets",     icon: "assets" });
  LifeUI.mount("#game");
  App.connect();
});
