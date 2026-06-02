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

  App.renderCareer = function () {
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
