/**
 * App.modals.education — schooling-related modals: exam questions, degree
 * award, course picker, plus the Occupation tab's drill-down modals
 * (Jobs list and Education panel).
 *
 * The Education modal embeds the in-school panel (grade bar + Study
 * Harder / Visit the Nurse / Drop Out) when the player is studying;
 * out of school it shows apply-to-uni / postgrad re-entry options.
 */
(function (App) {
  "use strict";

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

  // Occupation → Jobs drill-down. Lists every job the player qualifies
  // for; tapping a row applies via apply-for-job.
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

  // Occupation → Education drill-down. When in school, embeds the
  // school panel (grade bar + Study Harder / Visit the Nurse / Drop
  // Out). When out of school, shows the re-entry options (apply to
  // uni / postgrad / doctorate). Designed as a list so future tracks
  // (Community College, Medical, Law, Dental) just append rows.
  App.openEducationModal = function () {
    const s = this.state;
    const edu = s.education || {};
    const age = (s.character && s.character.age) || 0;
    const items = [];

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
})(window.App = window.App || {});
