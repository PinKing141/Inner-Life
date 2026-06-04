/**
 * App.occupation helpers — shared by the Life screen entry-card +
 * the Education/Jobs modals. The Occupation tab itself is gone; School
 * and Special Careers are opened as overlay modals from the Life screen.
 * What survives here:
 *   - occupationLocked(state) → greys the School entry-card while the
 *     player is too young for school
 *   - _gradeForSmarts / _schoolName / _gradeBarHTML / _eligibleJobs /
 *     _educationSummary — used by openJobsModal + openEducationModal
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

})(window.App = window.App || {});
