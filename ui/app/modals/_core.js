/**
 * App.modals._core — pending_* fields on the snapshot drive which modal
 * is open. computeModalKey() turns the snapshot into a stable key,
 * syncModal() raises/closes the LifeUI modal accordingly, and
 * raiseModalFor() dispatches to the right per-domain raise* helper.
 *
 * The actual raise* helpers live next door in ui/app/modals/<domain>.js.
 * To add a new pending-* surface:
 *   1. Add a key prefix here (computeModalKey)
 *   2. Add a routing branch (raiseModalFor)
 *   3. Define the raise helper in the relevant per-domain file.
 */
(function (App) {
  "use strict";

  App.syncModal = function () {
    const key = this.computeModalKey(this.state);
    if (key === this.currentModalKey) return;
    this.currentModalKey = key;
    if (key === null) { LifeUI.closeModal(); return; }
    this.raiseModalFor(key, this.state);
  };

  App.computeModalKey = function (s) {
    if (s.pending_event && s.pending_event_id) return "event:" + s.pending_event_id + ":" + s.tick;
    if (s.pending_job_offer) return "offer:" + (s.pending_job_offer.title || "") + ":" + s.tick;
    if (s.pending_promotion) return "promo:" + (s.pending_promotion.title || "") + ":" + s.tick;
    if (s.pending_job_loss) return "loss:" + (s.pending_job_loss.title || "") + ":" + s.tick;
    if (s.pending_career_setback) return "setback:" + (s.pending_career_setback.type || "") + ":" + s.tick;
    if (s.job_application_error) return "reject:" + s.tick + ":" + (s.job_application_error || "").slice(0, 24);
    if (s.exam && s.exam.current && !s.exam.finished) return "exam:" + s.exam.index;
    if (s.education && s.education.degree_award_pending) return "degree:" + s.tick;
    if (s.education && s.education.awaiting_university_choice) return "uni:" + s.tick;
    if (s.pending_birth) return "birth:" + s.pending_birth.npc_id + ":" + s.tick;
    if (s.pending_milestone) return "milestone:" + s.pending_milestone.id + ":" + s.tick;
    if (s.pending_crime_outcome) return "crime:" + (s.pending_crime_outcome.crime_id || "?") + ":" + s.tick + ":" + (s.feed ? s.feed.length : 0);
    if (s.mode === "DEATH" && !this.deathShown) { this.deathShown = true; return "death"; }
    return null;
  };

  App.raiseModalFor = function (key, s) {
    if (key.startsWith("event:"))         this.raiseEventModal(s.pending_event);
    else if (key.startsWith("offer:"))    this.raiseJobOfferModal(s.pending_job_offer);
    else if (key.startsWith("promo:"))    this.raisePromotionModal(s.pending_promotion);
    else if (key.startsWith("loss:"))     this.raiseJobLossModal(s.pending_job_loss);
    else if (key.startsWith("setback:"))  this.raiseSetbackModal(s.pending_career_setback);
    else if (key.startsWith("reject:"))   this.raiseRejectionModal(s.job_application_error);
    else if (key.startsWith("exam:"))     this.raiseExamModal(s.exam);
    else if (key.startsWith("degree:"))   this.raiseDegreeModal(s.education);
    else if (key.startsWith("uni:"))      this.raiseUniversityModal(s);
    else if (key.startsWith("birth:"))    this.raiseBirthModal(s.pending_birth);
    else if (key.startsWith("milestone:")) this.raiseMilestoneModal(s.pending_milestone);
    else if (key.startsWith("crime:"))    this.raiseCrimeOutcomeModal(s.pending_crime_outcome);
    else if (key === "death")             this.raiseDeathModal(s);
  };
})(window.App = window.App || {});
