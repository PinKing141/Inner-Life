/**
 * App.screens.occupation — render the Occupation tab + helpers shared
 * with the Education modal.
 *
 * Landing layout (BitLife-style category page):
 *   • Current Job + Career Actions (when employed)
 *   • Occupation: Jobs · Education (drill-down rows)
 *
 * Both drill-down rows open modals defined in ui/app/modals/education.js
 * (openJobsModal / openEducationModal). The grade helpers + job filter
 * live here because the landing's subtitle counts use them too.
 */
(function (App) {
  "use strict";

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

  App.renderOccupation = function () {
    const s = this.state;

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
})(window.App = window.App || {});
