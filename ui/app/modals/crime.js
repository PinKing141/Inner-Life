/**
 * App.modals.crime — Clean Getaway / Busted outcome modal.
 *
 * Same shell for both outcomes, differentiated by `caught`:
 * busted shows in notice/red with a lock icon, clean getaway shows
 * award/gold with a gem icon.
 */
(function (App) {
  "use strict";

  App.raiseCrimeOutcomeModal = function (o) {
    if (!o) return;
    const caught = !!o.caught;
    LifeUI.modal({
      kind: caught ? "notice" : "award",
      title: o.title || (caught ? "Busted" : "Clean Getaway"),
      dismissable: true,
      blocks: [{ type: "award",
        icon: caught ? "lock" : "gem",
        title: o.title || "",
        subtitle: o.text || "" }],
      actions: [{
        label: caught ? "Take it on the chin" : "Get out of here",
        variant: caught ? "ghost" : "primary",
        action: "ack-crime-outcome",
      }],
    });
  };
})(window.App = window.App || {});
