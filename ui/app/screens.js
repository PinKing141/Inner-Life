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
