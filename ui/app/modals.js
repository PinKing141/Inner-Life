/**
 * App.modals — pending_* fields on the snapshot are the source of truth for
 * which modal is open. computeModalKey() turns the snapshot into a stable
 * key, syncModal() raises/closes accordingly. raise* helpers build the
 * LifeUI modal spec for each kind of pending state.
 */
(function (App) {
  "use strict";

  App.syncModal = function () {
    const key = this.computeModalKey(this.state);
    if (key === this.currentModalKey) return;
    this.currentModalKey = key;
    if (key === null) { LifeUI.closeModal(); return; }
    this.raiseModalFor(key, this.state);
  };

  App.computeModalKey = function (s) {
    if (s.pending_event && s.pending_event_id) return "event:" + s.pending_event_id + ":" + s.tick;
    if (s.pending_job_offer) return "offer:" + (s.pending_job_offer.title || "") + ":" + s.tick;
    if (s.pending_promotion) return "promo:" + (s.pending_promotion.title || "") + ":" + s.tick;
    if (s.pending_job_loss) return "loss:" + (s.pending_job_loss.title || "") + ":" + s.tick;
    if (s.pending_career_setback) return "setback:" + (s.pending_career_setback.type || "") + ":" + s.tick;
    if (s.job_application_error) return "reject:" + s.tick + ":" + (s.job_application_error || "").slice(0, 24);
    if (s.exam && s.exam.current && !s.exam.finished) return "exam:" + s.exam.index;
    if (s.education && s.education.degree_award_pending) return "degree:" + s.tick;
    if (s.education && s.education.awaiting_university_choice) return "uni:" + s.tick;
    if (s.pending_birth) return "birth:" + s.pending_birth.npc_id + ":" + s.tick;
    if (s.pending_milestone) return "milestone:" + s.pending_milestone.id + ":" + s.tick;
    if (s.mode === "DEATH" && !this.deathShown) { this.deathShown = true; return "death"; }
    return null;
  };

  App.raiseModalFor = function (key, s) {
    if (key.startsWith("event:"))   this.raiseEventModal(s.pending_event);
    else if (key.startsWith("offer:"))   this.raiseJobOfferModal(s.pending_job_offer);
    else if (key.startsWith("promo:"))   this.raisePromotionModal(s.pending_promotion);
    else if (key.startsWith("loss:"))    this.raiseJobLossModal(s.pending_job_loss);
    else if (key.startsWith("setback:")) this.raiseSetbackModal(s.pending_career_setback);
    else if (key.startsWith("reject:"))  this.raiseRejectionModal(s.job_application_error);
    else if (key.startsWith("exam:"))    this.raiseExamModal(s.exam);
    else if (key.startsWith("degree:"))  this.raiseDegreeModal(s.education);
    else if (key.startsWith("uni:"))     this.raiseUniversityModal(s);
    else if (key.startsWith("birth:"))   this.raiseBirthModal(s.pending_birth);
    else if (key.startsWith("milestone:")) this.raiseMilestoneModal(s.pending_milestone);
    else if (key === "death")            this.raiseDeathModal(s);
  };

  App.raiseBirthModal = function (b) {
    if (!b) return;
    const descriptor = (b.gender === "Female") ? "girl"
                     : (b.gender === "Male") ? "boy" : "child";
    const partner = b.partner_name || "your partner";
    LifeUI.modal({
      kind: "award", title: "It's a baby!", dismissable: false,
      blocks: [
        { type: "award", icon: "heart",
          title: `You and ${partner} welcomed a baby ${descriptor}.`,
          subtitle: "What will you name them?" },
        { type: "text-input",
          key: "babyName",
          label: "First name",
          value: b.suggested_name || "",
          placeholder: "Their name",
          maxLength: 32 },
      ],
      actions: [
        { label: "Name them", variant: "primary", action: "name-baby",
          payload: { npc_id: b.npc_id } },
      ],
    });
  };

  // Icon + accent per milestone "kind" — keeps the visual language tight
  // without inventing per-id assets. New milestones land here as needed.
  const MILESTONE_LOOK = {
    coming_of_age: { icon: "key",         accent: "var(--gold)" },
    decade:        { icon: "cake",        accent: "var(--accent)" },
    retirement:    { icon: "rocking",     accent: "var(--accent)" },
    centenarian:   { icon: "crown",       accent: "var(--gold)" },
  };

  App.raiseMilestoneModal = function (m) {
    if (!m) return;
    const look = MILESTONE_LOOK[m.kind] || { icon: "star", accent: "var(--accent)" };
    LifeUI.modal({
      kind: "award", title: m.title || "A milestone", dismissable: true,
      blocks: [{ type: "award", icon: look.icon,
        title: m.title || "",
        subtitle: m.subtitle || "" }],
      actions: [{ label: "Carry on", variant: "primary", action: "ack-milestone" }],
    });
  };

  App.raiseEventModal = function (ev) {
    LifeUI.modal({
      kind: "event", title: ev.title || "A Decision",
      blocks: [
        { type: "text", text: ev.text || "" },
        { type: "choices", action: "event-choice",
          choices: (ev.choices || []).map((c, i) => ({ id: i, label: c.text || "" })) },
      ],
    });
  };

  App.raiseJobOfferModal = function (o) {
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
  };

  App.raisePromotionModal = function (p) {
    LifeUI.modal({
      kind: "award", title: "Promoted",
      blocks: [{ type: "award", icon: "trophy", title: p.title,
        subtitle: `${p.employer || ""} · £${(p.salary || 0).toLocaleString()} (+${p.pct}%)` }],
      actions: [{ label: "Excellent", variant: "primary", action: "ack-promotion" }],
    });
  };

  App.raiseJobLossModal = function (l) {
    LifeUI.modal({
      kind: "notice",
      title: l.fired ? "You Were Fired" : "You Were Laid Off",
      blocks: [{ type: "text", text:
        `You lost your position as ${l.title} at ${l.employer || "your employer"} — ${l.reason || "let go"}.` }],
      actions: [{ label: "Acknowledge", variant: "ghost", action: "ack-job-loss" }],
    });
  };

  App.raiseSetbackModal = function (c) {
    LifeUI.modal({
      kind: "notice",
      title: c.type === "demotion" ? "Demoted" : "Pay Cut",
      blocks: [{ type: "text", text:
        c.type === "demotion"
          ? `You were demoted to ${c.title} (−${c.pct}%).`
          : `Your salary was cut by ${c.pct}% (${c.reason || ""}).` }],
      actions: [{ label: "Acknowledge", variant: "ghost", action: "ack-setback" }],
    });
  };

  App.raiseRejectionModal = function (msg) {
    LifeUI.modal({
      kind: "notice", title: "Application Rejected", dismissable: true,
      blocks: [{ type: "text", text: msg || "" }],
      actions: [{ label: "Close", variant: "ghost", action: "clear-rejection" }],
    });
  };

  App.raiseExamModal = function (exam) {
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
  };

  App.raiseDegreeModal = function (edu) {
    LifeUI.modal({
      kind: "award", title: "Degree Awarded",
      blocks: [{ type: "award", icon: "cap",
        title: edu.degree_award_label || "Degree",
        subtitle: `Congratulations on completing your studies at ${edu.university_name || "your university"}.` }],
      actions: [{ label: "Wonderful", variant: "primary", action: "ack-degree" }],
    });
  };

  App.raiseUniversityModal = function (s) {
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
  };

  App.raiseDeathModal = function (s) {
    const ch = s.character || {};
    // Phase 5: if the player left living heirs, the modal becomes a
    // generational hand-off rather than a terminal screen. Each heir
    // surfaces as a picker row carrying their npc_id; clicking routes
    // through `continue-as-heir` -> bridge.continueAsHeir.
    const heirs = s.eligible_heirs || [];
    const blocks = [{ type: "award", icon: "hourglass",
      title: `${ch.name || "You"} died at ${ch.age || 0}`,
      subtitle: heirs.length
        ? "Your line endures — choose an heir to carry on."
        : "Your story is complete. Open the menu to start another life." }];

    if (heirs.length) {
      blocks.push({ type: "list", items: heirs.map(h => ({
        icon: "infant", accent: "var(--gold)",
        title: `${h.name} — age ${h.age}`,
        subtitle: `Continue as your child`,
        trailing: { kind: "chevron" },
        action: "continue-as-heir", payload: h.npc_id,
      })) });
    }

    LifeUI.modal({
      kind: "award", title: "End of Life", dismissable: true,
      blocks,
      actions: [{ label: "Close", variant: "ghost", action: "__close" }],
    });
  };

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
  };
})(window.App = window.App || {});
