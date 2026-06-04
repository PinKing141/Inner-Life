/**
 * App.screens._helpers — shared helpers used by multiple screen renderers.
 * Just the small utilities that don't belong to one domain (imgTag for
 * country flags, stageFor for the identity-area age-band label).
 *
 * Each ui/app/screens/*.js file augments the global `App` namespace
 * inside its own IIFE. Order across these files doesn't matter — all
 * augments are read at render time, not load time.
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
})(window.App = window.App || {});
