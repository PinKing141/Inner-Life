/**
 * App.screens — render the four list-based screens (activities, career,
 * relations, assets) from a snapshot. Pure projection: snapshot dicts in,
 * LifeUI.renderScreen() calls out. No state, no bridge calls.
 *
 * Attaches methods to the global `App` namespace defined in app.js.
 */
(function (App) {
  "use strict";

  function imgTag(src) {
    return `<img src="${src}" alt="" style="display:block;width:100%;height:100%;object-fit:cover">`;
  }
  App.imgTag = imgTag;

  App.stageFor = function (age, edu) {
    if (edu && edu.in_school) return edu.level === "University" ? "University" : "School";
    if (age < 2) return "Infant";
    if (age < 5) return "Toddler";
    if (age < 13) return "Child";
    if (age < 18) return "Teenager";
    if (age < 30) return "Young Adult";
    if (age < 55) return "Adult";
    if (age < 70) return "Mature Adult";
    return "Senior";
  };

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

  // Whether the Occupation tab should be greyed (player too young for
  // school OR work). Drives setIdentity({occupationLocked}) — the tab
  // is still tappable, but the panel renders a "come back later" tile.
  App.occupationLocked = function (s) {
    const edu = s.education || {};
    if (edu.in_school) return false;
    return ((s.character && s.character.age) || 0) < 5;
  };

  // Convert player smarts to a letter grade for the school panel.
  // 6 tiers: F < D < C < B < A < A+ so progression is visible without
  // being grade-inflation-y.
  App._gradeForSmarts = function (smarts) {
    if (smarts >= 96) return "A+";
    if (smarts >= 86) return "A";
    if (smarts >= 71) return "B";
    if (smarts >= 56) return "C";
    if (smarts >= 36) return "D";
    return "F";
  };

  // The school name string — currently driven by edu.level since the
  // sim doesn't model specific named schools yet. Uni uses the real
  // university_name. Future: per-edu-tier school catalogue.
  App._schoolName = function (edu) {
    if (edu.level === "University") {
      return edu.university_name || "University";
    }
    if (edu.level === "Secondary Education") return "Secondary School";
    if (edu.level === "Primary School") return "Primary School";
    return "School";
  };

  // Build the grade-bar HTML block. Pure markup — no event handlers.
  // Tiers map to fill percentages so the bar visibly grows with smarts.
  App._gradeBarHTML = function (smarts) {
    const grade = App._gradeForSmarts(smarts);
    const pct = Math.max(0, Math.min(100, smarts));
    const tone = smarts >= 71 ? "good" : smarts >= 36 ? "warn" : "bad";
    return `<div class="ui-grade">` +
           `<div class="g-row"><span class="g-label">Grades</span>` +
           `<span class="g-value g-${tone}">${grade}</span></div>` +
           `<div class="g-bar"><div class="g-fill g-${tone}" ` +
                `style="width:${pct}%"></div></div>` +
           `</div>`;
  };

  // Shared job filter — same logic the snapshot would apply, lifted so
  // the Occupation panel can show the eligible list without a round-trip.
  App._eligibleJobs = function (s) {
    const age = (s.character && s.character.age) || 0;
    const smarts = (s.stats && s.stats.smarts) || 0;
    const edu = s.education || {};
    const order = ["None", "Primary School", "Secondary School",
                   "Secondary Education", "University"];
    const meets = (need) =>
      order.indexOf(edu.level || "None") >= order.indexOf(need);
    return (s.jobs || []).filter(j => {
      if (age < j.min_age) return false;
      if (smarts < j.min_smarts) return false;
      if (!meets(j.min_education)) return false;
      if (j.required_field &&
          (!edu.degree_completed || edu.degree_field !== j.required_field)) {
        return false;
      }
      return true;
    });
  };

  // Occupation tab landing — two drill-down rows (Jobs + Education).
  // Current-job + career actions appear here when employed; the
  // long lists live in modals (openJobsModal / openEducationModal)
  // so this landing stays a short BitLife-style category page.
  App.renderOccupation = function () {
    const s = this.state;
    const edu = s.education || {};
    const ch = s.character || {};
    const age = ch.age || 0;

    // Locked / too-young: panel is a single explanatory tile. The
    // tab is still tappable (per design feedback) so the player can
    // see why and watch the age requirement.
    if (App.occupationLocked(s)) {
      LifeUI.renderScreen("occupation", [{
        items: [{
          icon: "infant", accent: "var(--ink-faint)",
          title: "Too young",
          subtitle: "Nothing to do here yet. Age up to start school.",
          locked: true,
        }],
      }]);
      return;
    }

    const job = s.career;
    const groups = [];

    if (job) {
      groups.push({
        label: "Current Job",
        items: [{
          icon: "brief", accent: "var(--gold)",
          title: job.title,
          subtitle: `${job.employer || "Employer"} · £${(job.salary || 0).toLocaleString()}/yr · Perf ${job.performance}`,
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
    }

    // Occupation landing — two drill-down rows. Replaces the old long
    // "Available Jobs" + "Further Study" blocks; sub-pages are modals
    // (see openJobsModal / openEducationModal). The subtitles surface
    // the headline state so the player doesn't need to open the
    // sub-page just to glance.
    const eligibleJobsCount = App._eligibleJobs(s).length;
    groups.push({
      label: "Occupation",
      items: [
        { icon: "brief", accent: "var(--cat-money)",
          title: "Jobs",
          subtitle: job
            ? `Browse other listings · ${eligibleJobsCount} you qualify for`
            : (eligibleJobsCount > 0
                ? `${eligibleJobsCount} positions you qualify for`
                : "No jobs you qualify for yet — study to unlock more"),
          trailing: { kind: "chevron" },
          action: "open-jobs-modal" },
        { icon: "cap", accent: "var(--cat-education)",
          title: "Education",
          subtitle: App._educationSummary(s),
          trailing: { kind: "chevron" },
          action: "open-education-modal" },
      ],
    });

    LifeUI.renderScreen("occupation", groups);
  };

  // --- Occupation sub-page helpers ------------------------------------
  // (_eligibleJobs is defined once, earlier in this file.)


  // One-line state summary for the Education row's subtitle.
  App._educationSummary = function (s) {
    const edu = s.education || {};
    const age = (s.character && s.character.age) || 0;
    if (edu.in_school && edu.level === "University") {
      return `Studying ${edu.university_major || "an undeclared course"} · `
           + `${edu.study_years_left || 0}y left`;
    }
    if (edu.in_school) return "In school";
    if (!edu.degree_completed && age >= 18) return "Go back to school";
    if (edu.degree_completed && !edu.masters_completed) {
      return "Degree complete — Master's available";
    }
    if (edu.masters_completed && !edu.doctorate_completed) {
      return "Master's complete — Doctorate available";
    }
    if (edu.doctorate_completed) return "Doctorate complete";
    return "School in session";
  };

  // Jobs sub-page modal — the full eligible-job list. Replaces the
  // old "Available Jobs" group on the Career screen.
  App.openJobsModal = function () {
    const s = this.state;
    const jobs = App._eligibleJobs(s);
    const items = jobs.length === 0
      ? [{
          icon: "lock", accent: "var(--ink-faint)",
          title: "Nothing you qualify for yet",
          subtitle: "Bump your smarts or finish a degree to unlock more roles.",
          locked: true,
        }]
      : jobs.map(j => ({
          icon: "brief", accent: "var(--cat-money)",
          title: j.title,
          subtitle: `${j.employer || ""} · £${(j.salary || 0).toLocaleString()}/yr`,
          trailing: { kind: "chevron" },
          action: "apply-for-job", payload: j.job_id,
        }));
    LifeUI.modal({
      kind: "picker", title: "Jobs", dismissable: true,
      blocks: [{ type: "list", items }],
      actions: [{ label: "Close", variant: "ghost", action: "__close" }],
    });
  };

  // Education sub-page modal — currently a single category (general
  // schooling + further study). Designed as a list so v2 can drop in
  // Community College / Medical School / Law School / Post-grad
  // tracks as additional rows without restructuring the modal.
  App.openEducationModal = function () {
    const s = this.state;
    const edu = s.education || {};
    const age = (s.character && s.character.age) || 0;
    const items = [];

    // --- In school: show the current-school panel inline ---
    // The grade bar lives in a `text-html` block at the top of the
    // modal; the rows below are the school activities matching the
    // BitLife flow (Study Harder / Visit the Nurse / Drop Out).
    if (edu.in_school) {
      const inUni = edu.level === "University";
      items.push({
        icon: "cap", accent: "var(--cat-education)",
        title: App._schoolName(edu),
        subtitle: inUni
          ? `${edu.university_major || "Undeclared"} · ${edu.study_years_left || 0}y left`
          : `In session · grade ${App._gradeForSmarts(s.stats.smarts || 0)}`,
      });
      items.push({
        icon: "book", accent: "var(--c-smarts)",
        title: "Study Harder", subtitle: "Push your grades up",
        trailing: { kind: "chevron" },
        action: "do-activity", payload: "study",
      });
      items.push({
        icon: "doctor", accent: "var(--c-health)",
        title: "Visit the Nurse", subtitle: "Free clinic at school",
        trailing: { kind: "chevron" },
        action: "do-activity", payload: "school_nurse",
      });
      items.push({
        icon: "x", accent: "var(--c-bad)",
        title: "Drop Out",
        subtitle: inUni
          ? "Leave university without a degree"
          : "Leave school early — affects your job options later",
        trailing: { kind: "chevron" },
        action: inUni ? "drop-out-university" : "drop-out-school",
      });
    }

    // --- Not in school: re-entry options ---

    if (!edu.in_school && !edu.degree_completed && age >= 18) {
      items.push({
        icon: "cap", accent: "var(--cat-education)",
        title: "Apply to University",
        subtitle: "Open a course picker",
        trailing: { kind: "chevron" },
        action: "apply-university",
      });
    }

    if (!edu.in_school && edu.degree_completed && !edu.masters_completed) {
      items.push({
        icon: "cap", accent: "var(--cat-education)",
        title: "Enrol in a Master's Degree",
        subtitle: "Deepen your field; two years.",
        trailing: { kind: "chevron" },
        action: "enroll-postgrad", payload: "Master's Degree",
      });
    } else if (!edu.in_school && edu.masters_completed && !edu.doctorate_completed) {
      items.push({
        icon: "cap", accent: "var(--cat-education)",
        title: "Enrol in a Doctorate",
        subtitle: "Three or more years of research.",
        trailing: { kind: "chevron" },
        action: "enroll-postgrad", payload: "Doctorate",
      });
    }

    if (items.length === 0) {
      items.push({
        icon: "book", accent: "var(--ink-faint)",
        title: "No education options right now",
        subtitle: "Come back when you've aged up further.",
        locked: true,
      });
    }

    // When in school, prepend the grade-bar block above the list.
    const blocks = [];
    if (edu.in_school) {
      blocks.push({ type: "html", html: App._gradeBarHTML(s.stats.smarts || 0) });
    }
    blocks.push({ type: "list", items });

    LifeUI.modal({
      kind: "picker", title: "Education", dismissable: true,
      blocks,
      actions: [{ label: "Close", variant: "ghost", action: "__close" }],
    });
  };

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
      const rows = [
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
      return rows;
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

  // Crime screen — lists the ladder from snapshot.crimes (live success
  // chance + payout + sentence). Locked when the player is too young or
  // already incarcerated; tap fires `commit-crime` with the id.
  App.renderCrime = function () {
    const s = this.state;
    const incarcerated = s.crime && s.crime.is_incarcerated;
    const crimes = s.crimes || [];

    if (incarcerated) {
      const served = s.crime.years_served || 0;
      const total = s.crime.sentence_years || 0;
      LifeUI.renderScreen("crime", [{
        label: "In Prison",
        items: [{
          icon: "lock", accent: "var(--c-bad)",
          title: `Year ${served} of ${total}`,
          subtitle: "Your life resumes when you walk out. Age up to serve time.",
          locked: true,
        }],
      }]);
      return;
    }

    const items = crimes.map(c => {
      const pct = Math.round((c.success_chance || 0) * 100);
      const payoutMin = (c.payout_range || [0, 0])[0];
      const payoutMax = (c.payout_range || [0, 0])[1];
      const payoutStr = payoutMax === 0
        ? "no payout"
        : `£${payoutMin.toLocaleString()}–£${payoutMax.toLocaleString()}`;
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

    const groups = [{ label: "Crimes", items }];
    if (s.crime && s.crime.past_offences && s.crime.past_offences.length) {
      groups.push({
        label: "Record",
        items: s.crime.past_offences.map(o => ({
          icon: "pen", accent: "var(--c-bad)",
          title: o, subtitle: "On your permanent record.",
        })),
      });
    }
    LifeUI.renderScreen("crime", groups);
  };

  App.renderAssets = function () {
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

    // Cars/Assets v1 — owned vehicles + dealership listings
    const vehicles = s.vehicles || [];
    const carMarket = s.car_market || [];

    groups.push({
      label: "Vehicles",
      emptyText: "No cars yet.",
      items: vehicles.map(v => ({
        icon: "car", accent: "var(--gold)",
        title: `${v.brand} ${v.model}`,
        subtitle: `Owned ${v.age_years || 0}y · Bought £${(v.purchase_price || 0).toLocaleString()}`,
        trailing: { kind: "value", text: "£" + (v.current_value || 0).toLocaleString() },
        action: "sell-car", payload: v.instance_id,
      })),
    });

    groups.push({
      label: "Vehicle Market",
      emptyText: "No vehicles available.",
      items: carMarket.map(c => ({
        icon: "car",
        accent: c.available ? "var(--cat-money)" : "var(--ink-faint)",
        title: `${c.brand} ${c.model}`,
        subtitle: `${c.blurb}  ·  Top ${c.top_speed} · Prestige ${c.prestige}`,
        locked: !c.available,
        action: c.available ? "buy-car" : null,
        payload: c.id,
        trailing: c.available
          ? { kind: "value", text: "£" + (c.price || 0).toLocaleString() }
          : { kind: "badge", text: c.lock_reason || "Locked", icon: "lock" },
      })),
    });

    LifeUI.renderScreen("assets", groups);
  };

  App.openListingOptions = function (listingId) {
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
  };
})(window.App = window.App || {});
