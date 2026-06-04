/**
 * App.screens.crime — render the Crime tab (catalogue + record + prison).
 *
 * While incarcerated, the screen flips to a "Year N of M" tile and
 * hides the crime list. After release, the player's past offences
 * appear in a "Record" group below the live catalogue.
 */
(function (App) {
  "use strict";

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
})(window.App = window.App || {});
