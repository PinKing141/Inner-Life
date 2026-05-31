/**
 * App.creation — the 4-step new-game wizard (identity → origin → city →
 * talent). Pure UI flow with one terminal bridge call (newGameFull).
 * Step values accumulate on App.creation.
 */
(function (App) {
  "use strict";

  App.startCreation = function () {
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
  };

  App.creationStep = function (stepId, prefill) {
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
            id: c.code, label: c.name, flag: App.imgTag(c.flag_svg),
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
  };
})(window.App = window.App || {});
