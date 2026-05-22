/**
 * UI driver.
 *
 * The whole pattern: Python owns state. JS receives full state snapshots
 * (JSON strings) over the QWebChannel and rerenders against them. The only
 * stateful thing JS holds locally is the active tab.
 *
 * To preserve dev ergonomics, the bridge also has a Mock for browser-only
 * testing (open ui/index.html directly without Qt). The Mock provides a
 * minimal state machine so the UI is exercisable without launching Qt.
 */

const STAT_META = [
  { key: "happiness", label: "Happiness", color: "var(--stat-happy)", icon: "happiness" },
  { key: "health",    label: "Health",    color: "var(--stat-health)", icon: "health" },
  { key: "smarts",    label: "Smarts",    color: "var(--stat-smarts)", icon: "smarts" },
  { key: "looks",     label: "Looks",     color: "var(--stat-looks)",  icon: "looks" },
];

const ACTIVITIES = [
  { kind: "study",      name: "Study",       cost: "Free", icon: "book" },
  { kind: "gym",        name: "Train",       cost: "£30",  icon: "dumbbell" },
  { kind: "doctor",     name: "Doctor",      cost: "£100", icon: "stethoscope" },
  { kind: "spend_time", name: "Visit kin",   cost: "Free", icon: "people" },
];

const FALLBACK_NAMES = {
  Male: ["Oliver","George","Arthur","Noah","Muhammad","Leo","Oscar","Harry","Jack","Henry"],
  Female: ["Olivia","Amelia","Isla","Ava","Ivy","Freya","Lily","Florence","Mia","Willow"],
  NonBinary: ["Alex","Jordan","Charlie","Sam","Taylor","Morgan","Casey","Riley","Quinn","Rowan"],
};
const FALLBACK_SURNAMES = ["Smith","Johnson","Brown","Taylor","Wilson","Davies","Evans","Thomas","Roberts","Walker"];
const STAGE_ICONS = { Infant: "infant", School: "school", Teenager: "school", Career: "briefcase" };
const DATA_BASE = "flags-svg";

// How many recent feed entries to render. 100 years of play used to be one
// unbounded list — the UI would lag in late game. 30 is plenty for context.
const FEED_VISIBLE = 30;

const App = {
  bridge: null,
  state: null,
  activeTab: "feed",
  selectedNpcId: null,
  selectedJobId: null,
  countries: [], // populated from snapshot.countries — [{code,name,flag,currency,cities}]

  async ensureQtWebChannel() {
    if (typeof qt === "undefined" || typeof QWebChannel !== "undefined") {
      return;
    }

    await new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = "qrc:///qtwebchannel/qwebchannel.js";
      script.onload = resolve;
      script.onerror = () => reject(new Error("Failed to load qtwebchannel.js"));
      document.head.appendChild(script);
    });
  },

  async connect() {
    await this.ensureQtWebChannel();

    if (typeof QWebChannel !== "undefined" && typeof qt !== "undefined") {
      await new Promise((resolve) => {
        new QWebChannel(qt.webChannelTransport, (channel) => {
          this.bridge = channel.objects.bridge;
          this.bridge.stateChanged.connect((json) => {
            this.state = JSON.parse(json);
            this.onSnapshot();
            this.render();
          });
          resolve();
        });
      });
      const initial = await this.bridge.snapshot();
      this.state = JSON.parse(initial);
    } else {
      console.warn("QWebChannel not present; using mock bridge.");
      this.bridge = MockBridge.make((s) => { this.state = s; this.onSnapshot(); this.render(); });
      this.state = MockBridge.initial();
    }
    this.onSnapshot();
  },

  onSnapshot() {
    if (this.state && Array.isArray(this.state.countries) && this.state.countries.length) {
      this.countries = this.state.countries;
      populateCreation(this.countries);
    }
  },

  // ---- Verb wrappers ----

  async newGame(firstName, lastName, gender, country, city, talent) {
    let result;
    if (this.bridge.newGameFull) {
      result = await this.bridge.newGameFull(firstName, lastName, gender, country, city, talent);
    } else {
      const fullName = `${firstName} ${lastName}`.trim();
      result = await this.bridge.newGame(fullName, gender, country, talent);
    }
    if (typeof result === "string") this.state = JSON.parse(result);
    this.onSnapshot();
    this.render();
  },
  async ageUp() {
    const result = await this.bridge.ageUp();
    if (typeof result === "string") this.state = JSON.parse(result);
    this.render();
  },
  async choose(i) {
    const result = await this.bridge.choose(i);
    if (typeof result === "string") this.state = JSON.parse(result);
    this.render();
  },
  async applyForJob(jobId) {
    const result = await this.bridge.applyForJob(jobId);
    if (typeof result === "string") this.state = JSON.parse(result);
    if (this.state.pending_job_offer) this.selectedJobId = null;
    this.render();
  },
  async activity(kind) {
    const result = await this.bridge.activity(kind);
    if (typeof result === "string") this.state = JSON.parse(result);
    this.render();
  },
  async setUniversityPlan(attend, major) {
    const result = await this.bridge.setUniversityPlan(attend, major || "");
    if (typeof result === "string") this.state = JSON.parse(result);
    this.render();
  },
  async acknowledgeDegree() {
    const result = await this.bridge.acknowledgeDegree();
    if (typeof result === "string") this.state = JSON.parse(result);
    this.render();
  },
  async answerExam(i) {
    const result = await this.bridge.answerExam(i);
    if (typeof result === "string") this.state = JSON.parse(result);
    this.render();
  },
  async cheatExam() {
    const result = await this.bridge.cheatExam();
    if (typeof result === "string") this.state = JSON.parse(result);
    this.render();
  },
  async applyUniversity() {
    const result = await this.bridge.applyUniversity();
    if (typeof result === "string") this.state = JSON.parse(result);
    this.render();
  },
  async enrollPostgrad(program) {
    const result = await this.bridge.enrollPostgrad(program);
    if (typeof result === "string") this.state = JSON.parse(result);
    this.render();
  },
  async relationshipAction(npcId, action) {
    const result = await this.bridge.relationshipAction(npcId, action);
    if (typeof result === "string") this.state = JSON.parse(result);
    this.render();
  },
  async buyHome(id) {
    const result = await this.bridge.buyHome(id);
    if (typeof result === "string") this.state = JSON.parse(result);
    this.render();
  },
  async buyHomeMortgage(id) {
    const result = await this.bridge.buyHomeMortgage(id);
    if (typeof result === "string") this.state = JSON.parse(result);
    this.render();
  },
  async rentHome(id) {
    const result = await this.bridge.rentHome(id);
    if (typeof result === "string") this.state = JSON.parse(result);
    this.render();
  },
  async sellHome(id) {
    const result = await this.bridge.sellHome(id);
    if (typeof result === "string") this.state = JSON.parse(result);
    this.render();
  },
  async stopRenting() {
    const result = await this.bridge.stopRenting();
    if (typeof result === "string") this.state = JSON.parse(result);
    this.render();
  },
  async workHarder() {
    const result = await this.bridge.workHarder();
    if (typeof result === "string") this.state = JSON.parse(result);
    this.render();
  },
  async requestRaise() {
    const result = await this.bridge.requestRaise();
    if (typeof result === "string") this.state = JSON.parse(result);
    this.render();
  },
  async requestPromotion() {
    const result = await this.bridge.requestPromotion();
    if (typeof result === "string") this.state = JSON.parse(result);
    this.render();
  },
  async quitJob() {
    const result = await this.bridge.quitJob();
    if (typeof result === "string") this.state = JSON.parse(result);
    this.render();
  },
  async acknowledgeJobOffer() {
    const result = await this.bridge.acknowledgeJobOffer();
    if (typeof result === "string") this.state = JSON.parse(result);
    this.render();
  },
  async acknowledgeJobLoss() {
    const result = await this.bridge.acknowledgeJobLoss();
    if (typeof result === "string") this.state = JSON.parse(result);
    this.render();
  },
  async acknowledgeCareerSetback() {
    const result = await this.bridge.acknowledgeCareerSetback();
    if (typeof result === "string") this.state = JSON.parse(result);
    this.render();
  },
  async acknowledgePromotion() {
    const result = await this.bridge.acknowledgePromotion();
    if (typeof result === "string") this.state = JSON.parse(result);
    this.render();
  },
  async clearApplicationError() {
    const result = await this.bridge.clearApplicationError();
    if (typeof result === "string") this.state = JSON.parse(result);
    this.render();
  },
  // ---- Rendering ----

  render() {
    const s = this.state;
    const $ = (id) => document.getElementById(id);

    $("screen-creation").classList.toggle("hidden", s.mode !== "CREATION");
    $("screen-playing").classList.toggle("hidden", s.mode !== "PLAYING");
    $("screen-death").classList.toggle("hidden", s.mode !== "DEATH");

    if (s.mode === "PLAYING") this.renderPlaying();
    if (s.mode === "DEATH") this.renderDeath();
    this.renderModal();
    this.renderExamModal();
    this.renderUniversityModal();
    this.renderDegreeModal();
    this.renderRelationshipModal();
    this.renderJobApplyModal();
    this.renderJobOfferModal();
    this.renderPromotionModal();
    this.renderJobLossModal();
    this.renderCareerSetbackModal();
  },

  renderCareerSetbackModal() {
    const modal = document.getElementById("setback-modal");
    if (!modal) return;
    const s = this.state.pending_career_setback;
    const show = this.state.mode === "PLAYING" && !!s;
    modal.classList.toggle("hidden", !show);
    if (!show) return;
    const heading = s.type === "demotion" ? "Demoted" : "Pay cut";
    const sub = s.type === "demotion"
      ? `You were demoted to ${escapeHtml(s.title)}.`
      : `Your pay was cut at ${escapeHtml(s.employer)}.`;
    document.getElementById("setback-body").innerHTML = `
      <h2 class="popup-title popup-title-bad">${heading}</h2>
      <p class="popup-sub">${sub}</p>
      <div class="profile-fields">
        ${s.type === "demotion" ? `<div class="profile-field"><span>New Title</span><span>${escapeHtml(s.title)}</span></div>` : ""}
        <div class="profile-field"><span>Old Salary</span><span>£${(s.old_salary || 0).toLocaleString()}</span></div>
        <div class="profile-field"><span>New Salary</span><span>£${s.salary.toLocaleString()} (-${s.pct}%)</span></div>
        <div class="profile-field"><span>Reason</span><span>${escapeHtml(s.reason)}</span></div>
      </div>
      <p class="popup-continue">tap anywhere to continue</p>
    `;
  },

  renderJobLossModal() {
    const modal = document.getElementById("job-loss-modal");
    if (!modal) return;
    const loss = this.state.pending_job_loss;
    const show = this.state.mode === "PLAYING" && !!loss;
    modal.classList.toggle("hidden", !show);
    if (!show) return;
    const heading = loss.fired ? "You're fired" : "Laid off";
    document.getElementById("job-loss-body").innerHTML = `
      <h2 class="popup-title popup-title-bad">${heading}</h2>
      <p class="popup-sub">You lost your job as ${escapeHtml(loss.title)} at ${escapeHtml(loss.employer)}.</p>
      <div class="profile-fields">
        <div class="profile-field"><span>Former role</span><span>${escapeHtml(loss.title)}</span></div>
        <div class="profile-field"><span>Employer</span><span>${escapeHtml(loss.employer)}</span></div>
        <div class="profile-field"><span>Reason</span><span>${escapeHtml(loss.reason)}</span></div>
      </div>
      <button class="btn btn-primary" data-job-search style="width:100%;margin-top:8px">Look for a new job</button>
      <p class="popup-continue">or tap anywhere to continue</p>
    `;
    document.querySelector("#job-loss-body [data-job-search]").addEventListener("click", (e) => {
      e.stopPropagation();
      this.activeTab = "career";
      this.acknowledgeJobLoss();
    });
  },

  renderJobApplyModal() {
    const modal = document.getElementById("job-apply-modal");
    if (!modal) return;
    const id = this.selectedJobId;
    const job = id == null ? null : (this.state.jobs || []).find(j => j.job_id === id);
    // The offer/error popups take over once a decision is made.
    const show = this.state.mode === "PLAYING" && !!job && !this.state.pending_job_offer;
    modal.classList.toggle("hidden", !show);
    if (!show) return;

    const err = this.state.job_application_error;
    document.getElementById("job-apply-body").innerHTML = `
      <button class="modal-close" data-job-close aria-label="Close">&times;</button>
      <h3 class="job-apply-title">${escapeHtml(job.title)}</h3>
      <p class="job-apply-sub">Apply for this open position today!</p>
      <div class="profile-fields">
        <div class="profile-field"><span>Title</span><span>${escapeHtml(job.title)}</span></div>
        <div class="profile-field"><span>Career</span><span>${escapeHtml(job.title)}</span></div>
        <div class="profile-field"><span>Employer</span><span>${escapeHtml(job.employer || "—")}</span></div>
        <div class="profile-field"><span>Salary</span><span>£${job.salary.toLocaleString()}</span></div>
      </div>
      ${err ? `<p class="job-apply-error">${escapeHtml(err)}</p>` : ""}
      <button class="btn btn-primary" data-job-apply style="width:100%">Apply for this position</button>
    `;
    document.querySelector("#job-apply-body [data-job-apply]").addEventListener("click", () => this.applyForJob(id));
    document.querySelector("#job-apply-body [data-job-close]").addEventListener("click", () => {
      this.selectedJobId = null;
      if (this.state.job_application_error) { this.clearApplicationError(); } else { this.render(); }
    });
  },

  renderJobOfferModal() {
    const modal = document.getElementById("job-offer-modal");
    if (!modal) return;
    const offer = this.state.pending_job_offer;
    const show = this.state.mode === "PLAYING" && !!offer;
    modal.classList.toggle("hidden", !show);
    if (!show) return;
    document.getElementById("job-offer-body").innerHTML = `
      <h2 class="popup-title">Bringing home the bacon</h2>
      <p class="popup-sub">Welcome to ${escapeHtml(offer.employer)}!</p>
      <div class="profile-fields">
        <div class="profile-field"><span>Title</span><span>${escapeHtml(offer.title)}</span></div>
        <div class="profile-field"><span>Career</span><span>${escapeHtml(offer.career)}</span></div>
        <div class="profile-field"><span>Employer</span><span>${escapeHtml(offer.employer)}</span></div>
        <div class="profile-field"><span>Salary</span><span>£${offer.salary.toLocaleString()}</span></div>
      </div>
      <p class="popup-continue">tap anywhere to continue</p>
    `;
  },

  renderPromotionModal() {
    const modal = document.getElementById("promotion-modal");
    if (!modal) return;
    const promo = this.state.pending_promotion;
    const show = this.state.mode === "PLAYING" && !!promo;
    modal.classList.toggle("hidden", !show);
    if (!show) return;
    document.getElementById("promotion-body").innerHTML = `
      <h2 class="popup-title">Moving on up</h2>
      <p class="popup-sub">You have been promoted to ${escapeHtml(promo.title)}.</p>
      <div class="profile-fields">
        <div class="profile-field"><span>New Title</span><span>${escapeHtml(promo.title)}</span></div>
        <div class="profile-field"><span>New Salary</span><span>£${promo.salary.toLocaleString()} (+${promo.pct}%)</span></div>
        <div class="profile-field"><span>Career</span><span>${escapeHtml(promo.career)}</span></div>
        <div class="profile-field"><span>Employer</span><span>${escapeHtml(promo.employer)}</span></div>
      </div>
      <p class="popup-continue">tap anywhere to continue</p>
    `;
  },

  renderExamModal() {
    const modal = document.getElementById("exam-modal");
    if (!modal) return;
    const ex = this.state.exam;
    const show = this.state.mode === "PLAYING" && ex && ex.current && !ex.finished && !this.state.pending_event;
    modal.classList.toggle("hidden", !show);
    if (!show) return;

    const q = ex.current;
    document.getElementById("exam-progress").textContent =
      `${q.subject || "Final exam"} · Question ${ex.index + 1} of ${ex.total}`;
    document.getElementById("exam-question").textContent = q.prompt;
    const opts = document.getElementById("exam-options");
    opts.innerHTML = q.options.map((o, i) =>
      `<button class="event-choice${ex.revealed === i ? " revealed" : ""}" data-exam-answer="${i}">${escapeHtml(o)}</button>`
    ).join("");
    opts.querySelectorAll("[data-exam-answer]").forEach((btn) => {
      btn.addEventListener("click", () => this.answerExam(parseInt(btn.dataset.examAnswer, 10)));
    });
  },

  renderUniversityModal() {
    const modal = document.getElementById("university-modal");
    if (!modal) return;
    const edu = this.state.education;
    const show = this.state.mode === "PLAYING" && edu && edu.awaiting_university_choice && !this.state.pending_event;
    modal.classList.toggle("hidden", !show);
    if (!show) return;

    const admit = document.getElementById("university-admit");
    if (admit) {
      const parts = [];
      if (edu.final_school_grade) parts.push(`Final grade: ${edu.final_school_grade}`);
      if (edu.admitted_tier) parts.push(`${edu.admitted_tier} university`);
      if (edu.scholarship && edu.scholarship !== "none") parts.push(`${edu.scholarship} scholarship`);
      admit.textContent = parts.join(" · ");
    }

    const sel = document.getElementById("university-course");
    if (sel && !sel.dataset.populated) {
      const courses = this.state.courses || [];
      sel.innerHTML = "";
      courses.forEach((c) => sel.add(new Option(`${c.major} (${c.field.replace(/_/g, " ")})`, c.major)));
      sel.dataset.populated = "1";
    }
  },

  renderDegreeModal() {
    const modal = document.getElementById("degree-modal");
    if (!modal) return;
    const edu = this.state.education;
    const show = this.state.mode === "PLAYING" && edu && edu.degree_award_pending && !this.state.pending_event;
    modal.classList.toggle("hidden", !show);
    if (!show) return;
    const major = edu.university_major || "your subject";
    const uni = edu.university_name || "university";
    const label = edu.degree_award_label || "undergraduate degree";
    document.getElementById("degree-text").textContent =
      `You earned your ${label} in ${major} from ${uni}!`;
  },

  renderPlaying() {
    const s = this.state;
    const ch = s.character;
    const stage = stageForState(s);

    const flagEl = document.getElementById("hud-country-flag");
    if (flagEl) {
      if (s.country_flag_svg) {
        flagEl.innerHTML = `<img src="${escapeHtml(s.country_flag_svg)}" alt="${escapeHtml(ch.country)} flag" />`;
      } else {
        flagEl.textContent = s.country_flag || "";
      }
    }
    document.getElementById("hud-name").textContent = ch.name;
    document.getElementById("hud-meta").textContent = `${stage} · Age ${ch.age}`;
    const placeEl = document.getElementById("hud-place");
    if (placeEl) {
      const place = [ch.city, ch.country].filter(Boolean).join(", ");
      placeEl.textContent = place;
    }
    const moneyEl = document.getElementById("hud-money");
    moneyEl.textContent = formatMoney(s.money);
    moneyEl.classList.toggle("negative", s.money < 0);

    // Stats
    const grid = document.getElementById("stats-grid");
    grid.innerHTML = STAT_META.map(meta => `
      <div class="stat">
        <div class="stat-row">
          <span class="stat-label">${meta.label}</span>
          <span class="stat-value">${s.stats[meta.key]}</span>
        </div>
        <div class="stat-bar">
          <div class="stat-bar-fill" style="width:${s.stats[meta.key]}%;background:${meta.color}"></div>
        </div>
      </div>
    `).join("");

    // The leftmost nav button is the only one that changes with life stage:
    // Infant → School → Career, each with its own label and icon. Every other
    // tab stays fixed.
    const careerTab = document.querySelector('.tab[data-tab="career"]');
    const careerLabel = careerTab ? careerTab.querySelector('span:last-child') : null;
    const careerIcon = careerTab ? careerTab.querySelector('.tab-icon') : null;
    if (careerLabel) careerLabel.textContent = stage;
    if (careerIcon) {
      careerIcon.setAttribute('data-icon', STAGE_ICONS[stage] || 'briefcase');
      Icons.hydrate(careerIcon);
    }

    // Panel by tab. The feed is the home/records view; it has no dedicated
    // button — tapping a tab opens its panel, tapping it again returns here.
    const panel = document.getElementById("panel");
    let panelHtml = "";
    if (this.activeTab === "feed") panelHtml = this.renderFeed();
    else if (this.activeTab === "career") panelHtml = this.renderCareer();
    else if (this.activeTab === "relationships") panelHtml = this.renderRelationships();
    else if (this.activeTab === "activities") panelHtml = this.renderActivities();
    else if (this.activeTab === "assets") panelHtml = this.renderAssets();
    if (this.activeTab !== "feed") {
      panelHtml = `<button class="panel-back" data-action="back"><span data-icon="chevron-left"></span>Back</button>` + panelHtml;
    }
    panel.innerHTML = panelHtml;

    Icons.hydrate(panel);
    this.bindPanel(panel);

    document.querySelectorAll(".tab").forEach((el) => {
      el.classList.toggle("active", el.dataset.tab === this.activeTab);
    });

    const examActive = !!(s.exam && s.exam.current && !s.exam.finished);
    document.getElementById("btn-age-up").disabled =
      !!s.pending_event || examActive || !!s.pending_job_offer || !!s.pending_promotion ||
      !!s.pending_job_loss || !!s.pending_career_setback ||
      !!(s.education && (s.education.awaiting_exam || s.education.awaiting_university_choice || s.education.degree_award_pending));

    if (this.activeTab === "feed") {
      panel.scrollTop = 0;
    }
  },

  renderFeed() {
    // Only the last FEED_VISIBLE years to keep late-game responsive.
    const all = this.state.feed || [];
    const trimmed = all.slice(-FEED_VISIBLE);
    const omitted = all.length - trimmed.length;
    const entries = trimmed.slice().reverse();
    return `
      <p class="panel-heading">The record</p>
      ${entries.map(e => `
        <div class="feed-entry ${e.kind}">
          <div class="feed-age">${String(e.age).padStart(2, "0")}</div>
          <div class="feed-text">${escapeHtml(e.text)}</div>
        </div>
      `).join("")}
      ${omitted > 0 ? `<p class="feed-truncated">${omitted} earlier entries kept in the record</p>` : ""}
    `;
  },

  renderCareer() {
    const s = this.state;
    const edu = s.education;
    const career = s.career;
    const jobs = s.jobs || [];

    const studyingUni = edu.level === "University" && edu.in_school;
    const eduValue = studyingUni && edu.university_major
      ? `${escapeHtml(edu.university_major)} at ${escapeHtml(edu.university_name || "university")}`
      : escapeHtml(edu.level);

    return `
      <p class="panel-heading">Education</p>
      <div class="education-card">
        <div class="education-card-label">Current</div>
        <div class="education-card-value">${eduValue}</div>
        ${edu.in_school ? `<div class="education-card-state">Currently attending</div>` : ""}
      </div>
      ${edu.degree_completed ? `
      <div class="education-card">
        <div class="education-card-label">Degree</div>
        <div class="education-card-value">${escapeHtml(edu.university_major || "Undergraduate")}</div>
        <div class="education-card-state">Field: ${escapeHtml((edu.degree_field || "general").replace(/_/g, " "))}</div>
      </div>` : ""}

      ${this.renderStudyActions(edu)}

      <p class="panel-heading">Career</p>
      ${career ? `
        <div class="current-job">
          <div class="current-job-label">Current role</div>
          <div class="current-job-title">${escapeHtml(career.title)}</div>
          <div class="current-job-meta">${escapeHtml(career.employer || "")} · £${career.salary.toLocaleString()} / yr</div>
          <div class="profile-bar-row" style="margin-top:12px">
            <span class="profile-bar-label">Performance</span>
            <div class="profile-bar"><div class="profile-bar-fill" style="width:${career.performance || 0}%;background:var(--stat-smarts)"></div></div>
          </div>
          <div class="profile-actions" style="margin-top:12px">
            <button class="profile-action" data-action="work">Work harder</button>
            <button class="profile-action" data-action="ask-raise">Ask for a raise</button>
            <button class="profile-action" data-action="ask-promotion">Ask for a promotion</button>
            <button class="profile-action" data-action="quit">Quit job</button>
          </div>
        </div>
      ` : `
        <p class="unemployed">No present occupation.</p>
      `}

      <p class="panel-heading">Open roles</p>
      ${jobs.map(j => `
        <button class="job-row" data-action="apply" data-job="${j.job_id}">
          <div>
            <div class="job-row-title">${escapeHtml(j.title)}${j.track && j.track !== "general" ? ` <span class="job-track">(${j.track})</span>` : ""}</div>
            <div class="job-row-req">Req age ${j.min_age} · smarts ${j.min_smarts}${j.required_field ? ` · ${escapeHtml(j.required_field.replace(/_/g, " "))} degree` : ""}</div>
          </div>
          <div class="job-row-salary">£${(j.salary / 1000).toFixed(0)}k</div>
        </button>
      `).join("")}
    `;
  },

  renderStudyActions(edu) {
    const age = this.state.character.age;
    const buttons = [];
    if (age >= 18 && !edu.in_school && !edu.degree_completed) {
      buttons.push(`<button class="job-row" data-action="apply-uni"><div><div class="job-row-title">Apply to university</div><div class="job-row-req">Start an undergraduate degree</div></div></button>`);
    }
    if (edu.degree_completed && !edu.masters_completed && !edu.in_school) {
      buttons.push(`<button class="job-row" data-action="postgrad" data-program="Master's Degree"><div><div class="job-row-title">Apply for a Master's</div><div class="job-row-req">Graduate school · 2 years</div></div></button>`);
    }
    if (edu.masters_completed && !edu.doctorate_completed && !edu.in_school) {
      buttons.push(`<button class="job-row" data-action="postgrad" data-program="Doctorate"><div><div class="job-row-title">Apply for a Doctorate</div><div class="job-row-req">Postgraduate · 3 years</div></div></button>`);
    }
    if (!buttons.length) return "";
    return `<p class="panel-heading">Study</p>${buttons.join("")}`;
  },

  renderRelationships() {
    const rels = this.state.relationships || [];
    return `
      <p class="panel-heading">Relations</p>
      ${rels.length === 0 ? `<p class="unemployed">No-one of note.</p>` : ""}
      ${rels.map(r => {
        const c = r.relationship > 70 ? "var(--good)"
                : r.relationship > 30 ? "var(--warn)"
                : "var(--bad)";
        const kindLabel = r.alive ? r.kind : `${r.kind} (deceased)`;
        return `
          <button class="rel-row${r.alive ? "" : " deceased"}" data-action="profile" data-npc="${r.npc_id}">
            <div>
              <div class="rel-name">${escapeHtml(r.name)}</div>
              <div class="rel-kind">${escapeHtml(kindLabel)}</div>
            </div>
            <div class="rel-bar">
              <div class="rel-bar-fill" style="width:${r.relationship}%;background:${c}"></div>
            </div>
          </button>
        `;
      }).join("")}
    `;
  },

  renderRelationshipModal() {
    const modal = document.getElementById("relationship-modal");
    if (!modal) return;
    const id = this.selectedNpcId;
    const rel = id == null ? null : (this.state.relationships || []).find(r => r.npc_id === id);
    const show = this.state.mode === "PLAYING" && !!rel;
    modal.classList.toggle("hidden", !show);
    if (!show) return;

    const agent = (this.state.agents || []).find(a => a.npc_id === id);
    const relColor = rel.relationship > 70 ? "var(--good)" : rel.relationship > 30 ? "var(--warn)" : "var(--bad)";

    const fields = [["Relationship", rel.alive ? rel.kind : `${rel.kind} (deceased)`]];
    if (agent) {
      fields.push(["Age", `${agent.age}`]);
      fields.push(["Marital status", agent.marital_status || "Single"]);
      fields.push(["Education", agent.education || "None"]);
      fields.push(["Occupation", agent.job_title || "Unemployed"]);
      fields.push(["Bank", formatMoney(agent.money || 0)]);
    }

    const bar = (label, val, color) => `
      <div class="profile-bar-row">
        <span class="profile-bar-label">${label}</span>
        <div class="profile-bar"><div class="profile-bar-fill" style="width:${val}%;background:${color}"></div></div>
      </div>`;

    const bars = [bar("Relationship", rel.relationship, relColor)];
    if (agent) {
      bars.push(bar("Generosity", agent.generosity, "var(--stat-looks)"));
      bars.push(bar("Happiness", agent.happiness, "var(--stat-happy)"));
      bars.push(bar("Health", agent.health, "var(--stat-health)"));
      bars.push(bar("Smarts", agent.smarts, "var(--stat-smarts)"));
      bars.push(bar("Looks", agent.looks, "var(--stat-looks)"));
    }

    const actions = rel.alive ? `
      <div class="profile-actions">
        <button class="profile-action" data-rel-act="talk">Talk</button>
        <button class="profile-action" data-rel-act="compliment">Compliment</button>
        <button class="profile-action" data-rel-act="argue">Argue</button>
        <button class="profile-action" data-rel-act="gift">Give gift (£50)</button>
      </div>` : "";

    document.getElementById("relationship-body").innerHTML = `
      <div class="profile-header">
        <div class="profile-name">${escapeHtml(rel.name)}</div>
        <span class="profile-role">${escapeHtml(rel.kind)}</span>
      </div>
      <p class="modal-eyebrow">Profile</p>
      <div class="profile-fields">
        ${fields.map(([k, v]) => `<div class="profile-field"><span>${k}</span><span>${escapeHtml(v)}</span></div>`).join("")}
      </div>
      <div class="profile-bars">${bars.join("")}</div>
      ${actions}
    `;

    document.querySelectorAll("#relationship-body [data-rel-act]").forEach((btn) => {
      btn.addEventListener("click", () => this.relationshipAction(id, btn.dataset.relAct));
    });
  },

  renderActivities() {
    return `
      <p class="panel-heading">Activities</p>
      <div class="activities">
        ${ACTIVITIES.map(a => `
          <button class="activity" data-action="activity" data-kind="${a.kind}">
            <span class="activity-icon" data-icon="${a.icon}"></span>
            <span class="activity-body">
              <span class="activity-name">${a.name}</span>
              <span class="activity-cost">${a.cost}</span>
            </span>
            <span class="activity-chevron" data-icon="chevron"></span>
          </button>
        `).join("")}
      </div>
    `;
  },



  renderAssets() {
    const s = this.state;
    const career = s.career;
    const edu = s.education || {};
    const income = career ? career.salary : 0;
    const TUITION = { "University": 9250, "Master's Degree": 11000, "Doctorate": 4500 };
    let tuition = (edu.in_school && TUITION[edu.level]) || 0;
    if (edu.level === "University" && edu.scholarship === "full") tuition = 0;
    else if (edu.level === "University" && edu.scholarship === "partial") tuition = Math.floor(tuition / 2);
    const rent = s.rental ? (s.rental.rent || 0) : 0;
    const properties0 = s.properties || [];
    const mortgageOut = properties0.reduce((a, p) => a + ((p.mortgage_balance > 0) ? (p.mortgage_payment || 0) : 0), 0);
    const expenses = tuition + rent + mortgageOut;
    const money = s.money || 0;
    const netWorth = typeof s.net_worth === "number" ? s.net_worth : money;
    const properties = s.properties || [];
    const market = s.housing_market || [];

    const money_str = `${money < 0 ? "-" : ""}£${Math.abs(money).toLocaleString()}`;
    const nw_str = `${netWorth < 0 ? "-" : ""}£${Math.abs(netWorth).toLocaleString()}`;

    return `
      <p class="panel-heading">Assets</p>
      <div class="education-card">
        <div class="education-card-label">Net worth</div>
        <div class="education-card-value">${nw_str}</div>
      </div>
      <div class="education-card">
        <div class="education-card-label">Bank balance</div>
        <div class="education-card-value">${money_str}</div>
        ${money < 0 ? `<div class="education-card-state">In the negatives — income will pay this back</div>` : ""}
      </div>
      <div class="education-card">
        <div class="education-card-label">Income</div>
        <div class="education-card-value">£${income.toLocaleString()} / yr</div>
      </div>
      <div class="education-card">
        <div class="education-card-label">Expenses</div>
        <div class="education-card-value">£${expenses.toLocaleString()} / yr${rent > 0 ? " (incl. rent)" : ""}</div>
      </div>

      <p class="panel-heading">Property</p>
      ${s.rental ? `
        <div class="job-row">
          <div>
            <div class="job-row-title">${escapeHtml(s.rental.name)}</div>
            <div class="job-row-req">Renting · £${(s.rental.rent || 0).toLocaleString()}/yr</div>
          </div>
          <button class="profile-action" data-action="stop-rent">Move out</button>
        </div>` : ""}
      ${properties.map(p => `
        <div class="job-row">
          <div>
            <div class="job-row-title">${escapeHtml(p.name)}</div>
            <div class="job-row-req">Worth £${(p.value || 0).toLocaleString()}${p.mortgage_balance > 0 ? ` · mortgage £${p.mortgage_balance.toLocaleString()} (£${Math.round((p.mortgage_payment || 0) / 12).toLocaleString()}/mo)` : " · owned outright"}</div>
          </div>
          <button class="profile-action" data-action="sell-home" data-prop="${escapeHtml(p.id)}">Sell</button>
        </div>`).join("")}
      ${!s.rental && properties.length === 0 ? `<p class="unemployed">You have no home of your own.</p>` : ""}

      <p class="panel-heading">Property market</p>
      ${market.map(m => `
        <div class="job-row">
          <div>
            <div class="job-row-title">${escapeHtml(m.name)}</div>
            <div class="job-row-req">Buy £${m.price.toLocaleString()} · Rent £${m.rent.toLocaleString()}/yr</div>
          </div>
          <div class="market-actions">
            <button class="profile-action" data-action="rent-home" data-listing="${escapeHtml(m.id)}">Rent</button>
            <button class="profile-action" data-action="mortgage-home" data-listing="${escapeHtml(m.id)}">Mortgage</button>
            <button class="profile-action" data-action="buy-home" data-listing="${escapeHtml(m.id)}">Buy</button>
          </div>
        </div>`).join("")}
    `;
  },

  renderDeath() {
    const s = this.state;
    const ch = s.character;
    document.getElementById("death-name").textContent = ch.name;
    document.getElementById("death-meta").textContent = `Died at age ${ch.age}`;
    document.getElementById("death-money").textContent = formatMoney(s.money);
    document.getElementById("death-career").textContent = s.career ? s.career.title : "Unemployed";
  },

  renderModal() {
    const modal = document.getElementById("event-modal");
    const ev = this.state.pending_event;
    if (!ev) {
      modal.classList.add("hidden");
      return;
    }
    modal.classList.remove("hidden");
    document.getElementById("event-text").textContent = ev.text;
    const choices = document.getElementById("event-choices");
    choices.innerHTML = ev.choices.map((c, i) =>
      `<button class="event-choice" data-action="choose" data-i="${i}">${escapeHtml(c.text)}</button>`
    ).join("");
    choices.querySelectorAll("button").forEach((btn) => {
      btn.addEventListener("click", () => this.choose(parseInt(btn.dataset.i, 10)));
    });
  },

  bindPanel(root) {
    root.querySelectorAll("[data-action='back']").forEach((btn) => {
      btn.addEventListener("click", () => { this.activeTab = "feed"; this.render(); });
    });
    root.querySelectorAll("[data-action='apply']").forEach((btn) => {
      btn.addEventListener("click", () => {
        this.selectedJobId = btn.dataset.job;
        this.render();
      });
    });
    root.querySelectorAll("[data-action='work']").forEach((btn) => {
      btn.addEventListener("click", () => this.workHarder());
    });
    root.querySelectorAll("[data-action='ask-raise']").forEach((btn) => {
      btn.addEventListener("click", () => this.requestRaise());
    });
    root.querySelectorAll("[data-action='ask-promotion']").forEach((btn) => {
      btn.addEventListener("click", () => this.requestPromotion());
    });
    root.querySelectorAll("[data-action='quit']").forEach((btn) => {
      btn.addEventListener("click", () => {
        if (window.confirm("Are you sure you want to quit your job?")) this.quitJob();
      });
    });
    root.querySelectorAll("[data-action='activity']").forEach((btn) => {
      btn.addEventListener("click", () => this.activity(btn.dataset.kind));
    });
    root.querySelectorAll("[data-action='apply-uni']").forEach((btn) => {
      btn.addEventListener("click", () => this.applyUniversity());
    });
    root.querySelectorAll("[data-action='postgrad']").forEach((btn) => {
      btn.addEventListener("click", () => this.enrollPostgrad(btn.dataset.program));
    });
    root.querySelectorAll("[data-action='profile']").forEach((btn) => {
      btn.addEventListener("click", () => {
        this.selectedNpcId = parseInt(btn.dataset.npc, 10);
        this.render();
      });
    });
    root.querySelectorAll("[data-action='buy-home']").forEach((btn) => {
      btn.addEventListener("click", () => this.buyHome(btn.dataset.listing));
    });
    root.querySelectorAll("[data-action='mortgage-home']").forEach((btn) => {
      btn.addEventListener("click", () => this.buyHomeMortgage(btn.dataset.listing));
    });
    root.querySelectorAll("[data-action='rent-home']").forEach((btn) => {
      btn.addEventListener("click", () => this.rentHome(btn.dataset.listing));
    });
    root.querySelectorAll("[data-action='sell-home']").forEach((btn) => {
      btn.addEventListener("click", () => this.sellHome(btn.dataset.prop));
    });
    root.querySelectorAll("[data-action='stop-rent']").forEach((btn) => {
      btn.addEventListener("click", () => this.stopRenting());
    });
  },
};

// --------------------------------------------------------------------------
// Creation form (populated dynamically once the snapshot arrives)
// --------------------------------------------------------------------------

let _creationPopulated = false;

function populateCreation(countries) {
  const countrySel = document.getElementById("cre-country");
  if (!countrySel) return;

  // Wipe and rebuild once. Subsequent snapshots reuse the populated form.
  if (!_creationPopulated) {
    countrySel.innerHTML = "";
    countries.forEach((c) => {
      const opt = new Option(c.name, c.code);
      countrySel.add(opt);
    });
    // Default to the United Kingdom if available; otherwise first entry.
    const defaultIx = countries.findIndex((c) => c.code === "GB");
    countrySel.selectedIndex = defaultIx >= 0 ? defaultIx : 0;

    refreshCityOptions();
    refreshFlag();
    _creationPopulated = true;
  }
}

function selectedCountry() {
  const code = document.getElementById("cre-country").value;
  return (App.countries || []).find((c) => c.code === code);
}

function refreshFlag() {
  const flagEl = document.getElementById("cre-country-flag");
  const c = selectedCountry();
  if (!flagEl) return;
  if (c && c.flag_svg) {
    flagEl.innerHTML = `<img src="${escapeHtml(c.flag_svg)}" alt="${escapeHtml(c.name)} flag" />`;
  } else {
    flagEl.textContent = c ? c.flag || "" : "";
  }
}

function refreshCityOptions() {
  const citySel = document.getElementById("cre-city");
  if (!citySel) return;
  const c = selectedCountry();
  citySel.innerHTML = "";
  if (c && c.cities) {
    c.cities.forEach((city) => citySel.add(new Option(city, city)));
  }
}

function pickRandom(list) {
  return list[Math.floor(Math.random() * list.length)];
}

function fillRandomName() {
  const gender = document.getElementById("cre-gender").value;
  const list = FALLBACK_NAMES[gender] || FALLBACK_NAMES.NonBinary;
  document.getElementById("cre-first-name").value = pickRandom(list);
  document.getElementById("cre-last-name").value = pickRandom(FALLBACK_SURNAMES);
}

// --------------------------------------------------------------------------
// Helpers
// --------------------------------------------------------------------------

function stageForState(state) {
  const age = state.character.age;
  const inSchool = state.education && state.education.in_school;
  if (inSchool) return "School";
  if (age < 5) return "Infant";
  if (age >= 18) return "Career";
  return "Teenager";
}

function formatMoney(n) {
  const sign = n < 0 ? "-" : "";
  return `${sign}£${Math.abs(n).toLocaleString()}`;
}

function escapeHtml(str) {
  return String(str).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]
  );
}

function buildCountryPicker() {
  const root = document.getElementById("cre-country-picker");
  const hidden = document.getElementById("cre-country");
  if (!root || typeof COUNTRIES_BY_CONTINENT === "undefined") return;

  root.innerHTML = COUNTRIES_BY_CONTINENT.map(group => `
    <div class="country-group">
      <div class="country-group-label">${escapeHtml(group.name)}</div>
      <div class="country-grid">
        ${group.countries.map(c => `
          <button type="button" class="country-option" data-code="${c.code}" data-name="${escapeHtml(c.name)}">
            <span class="country-flag"><img src="${DATA_BASE}/${group.name.toLowerCase().replace(/\s+/g,'-')}/${c.code.toLowerCase()}.svg" alt="${escapeHtml(c.name)} flag" /></span>
            <span class="country-name">${escapeHtml(c.name)}</span>
          </button>
        `).join("")}
      </div>
    </div>
  `).join("");

  const setSelected = (btn) => {
    root.querySelectorAll(".country-option.selected").forEach(b => b.classList.remove("selected"));
    btn.classList.add("selected");
    hidden.value = btn.dataset.name;
  };

  root.querySelectorAll(".country-option").forEach((btn) => {
    btn.addEventListener("click", () => setSelected(btn));
  });

  // Default to first country (United Kingdom).
  const first = root.querySelector(".country-option");
  if (first) setSelected(first);
}

// --------------------------------------------------------------------------
// Mock bridge — runs entirely in the browser, just enough to design against.
// --------------------------------------------------------------------------

const MockBridge = (() => {
  const MOCK_COURSES = [
    { major: "Computer Science", field: "technology" },
    { major: "Physics", field: "science" },
    { major: "Medicine", field: "medicine" },
    { major: "Law", field: "law" },
    { major: "Fine Art", field: "arts" },
  ];
  const MOCK_COUNTRIES = [
    {
      code: "GB",
      name: "United Kingdom",
      flag: "🇬🇧",
      flag_svg: "flags-svg/europe/gb.svg",
      currency: "GBP",
      cities: ["London","Manchester","Birmingham","Edinburgh","Glasgow","Liverpool","Bristol"],
    },
    {
      code: "US",
      name: "United States",
      flag: "🇺🇸",
      flag_svg: "flags-svg/north-america/us.svg",
      currency: "USD",
      cities: ["New York","Los Angeles","Chicago","Houston","Phoenix","Philadelphia","San Francisco"],
    },
    {
      code: "JP",
      name: "Japan",
      flag: "🇯🇵",
      flag_svg: "flags-svg/asia/jp.svg",
      currency: "JPY",
      cities: ["Tokyo","Osaka","Yokohama","Nagoya","Sapporo","Kyoto","Fukuoka"],
    },
  ];

  let state = { mode: "CREATION", countries: MOCK_COUNTRIES };
  let pushTo = null;

  function broadcast() {
    if (pushTo) pushTo(state);
  }

  return {
    initial() { return { mode: "CREATION", countries: MOCK_COUNTRIES }; },
    make(onChange) {
      pushTo = onChange;
      return {
        async snapshot() { return JSON.stringify(state); },
        async newGame(name, gender, country, talent) {
          return this.newGameFull(name, "", gender, country, "", talent);
        },
        async newGameFull(firstName, lastName, gender, country, city, talent) {
          const cn = MOCK_COUNTRIES.find((c) => c.code === country || c.name === country) || MOCK_COUNTRIES[0];
          state = {
            mode: "PLAYING",
            character: {
              name: `${firstName} ${lastName}`.trim(),
              first_name: firstName,
              last_name: lastName,
              gender,
              country: cn.name,
              city: city || cn.cities[0],
              talent,
              age: 0,
              alive: true,
            },
            stats: { happiness: 100, health: 90, smarts: 60, looks: 60 },
            money: 0,
            relationships: [
              { npc_id: 1, name: `Helen ${lastName}`.trim(), kind: "Mother", relationship: 90, alive: true },
              { npc_id: 2, name: `Robert ${lastName}`.trim(), kind: "Father", relationship: 90, alive: true },
            ],
            agents: [
              { npc_id: 1, name: `Helen ${lastName}`.trim(), role: "Mother", age: 38, gender: "Female", health: 85, happiness: 70, smarts: 60, looks: 60, generosity: 72, money: 15000, job_title: "School Psychologist", marital_status: "Married", education: "University", alive: true },
              { npc_id: 2, name: `Robert ${lastName}`.trim(), role: "Father", age: 41, gender: "Male", health: 80, happiness: 65, smarts: 55, looks: 55, generosity: 48, money: 8000, job_title: "Engineer", marital_status: "Married", education: "Secondary Education", alive: true },
            ],
            career: null,
            education: {
              level: "None", in_school: false, university_intent: "undecided",
              university_major: "", university_name: "", degree_field: "",
              degree_completed: false, masters_completed: false, doctorate_completed: false,
              study_years_left: 0, scholarship: "none",
              awaiting_university_choice: false, degree_award_pending: false, degree_award_label: "",
              awaiting_exam: false, exam_taken: false, final_school_grade: "",
              exam_correct: 0, admitted_tier: "",
            },
            courses: MOCK_COURSES,
            exam: null,
            feed: [{ age: 0, text: `You were born in ${city || cn.cities[0]}, ${cn.name}.`, kind: "special" }],
            pending_event: null,
            tick: 0,
            country_flag: cn.flag,
            country_flag_svg: cn.flag_svg,
            country_code: cn.code,
            currency: cn.currency,
            countries: MOCK_COUNTRIES,
            jobs: [
              { job_id: "retail",  title: "Retail Assistant", min_age: 16, min_smarts: 0, salary: 15000, track: "general", employer: "City Holdings" },
              { job_id: "barista", title: "Barista",          min_age: 16, min_smarts: 0, salary: 16000, track: "general", employer: "Solutions Group" },
            ],
            pending_job_offer: null,
            pending_promotion: null,
            pending_job_loss: null,
            pending_career_setback: null,
            job_application_error: null,
            properties: [],
            rental: null,
            net_worth: 0,
            housing_market: [
              { id: "studio-1", name: "Studio Flat", price: 85000, rent: 7200 },
              { id: "terrace-1", name: "Terraced House", price: 240000, rent: 13200 },
              { id: "detached-1", name: "Detached House", price: 520000, rent: 22800 },
            ],
          };
          broadcast();
          return JSON.stringify(state);
        },
        async ageUp() {
          state.character.age += 1;
          state.feed.push({ age: state.character.age, text: `You are now ${state.character.age} years old.`, kind: "neutral" });
          broadcast();
          return JSON.stringify(state);
        },
        async choose() { broadcast(); return JSON.stringify(state); },
        async applyForJob(jobId) {
          const job = (state.jobs || []).find(j => j.job_id === jobId);
          if (job) {
            state.career = { job_id: job.job_id, title: job.title, salary: job.salary, employer: job.employer, career: job.title, level: 0, performance: 50 };
            state.pending_job_offer = { title: job.title, career: job.title, employer: job.employer, salary: job.salary };
            state.job_application_error = null;
          }
          broadcast();
          return JSON.stringify(state);
        },
        async activity() { broadcast(); return JSON.stringify(state); },
        async workHarder() {
          if (state.career) state.career.performance = Math.min(100, (state.career.performance || 0) + 8);
          broadcast();
          return JSON.stringify(state);
        },
        async requestRaise() {
          if (state.career) state.career.salary = Math.round(state.career.salary * 1.08);
          broadcast();
          return JSON.stringify(state);
        },
        async requestPromotion() {
          if (state.career) {
            state.career.level = (state.career.level || 0) + 1;
            state.career.salary = Math.round(state.career.salary * 1.15);
            state.pending_promotion = { title: state.career.title, career: state.career.career, employer: state.career.employer, salary: state.career.salary, pct: 15 };
          }
          broadcast();
          return JSON.stringify(state);
        },
        async quitJob() { state.career = null; broadcast(); return JSON.stringify(state); },
        async acknowledgeJobOffer() { state.pending_job_offer = null; broadcast(); return JSON.stringify(state); },
        async acknowledgePromotion() { state.pending_promotion = null; broadcast(); return JSON.stringify(state); },
        async acknowledgeJobLoss() { state.pending_job_loss = null; broadcast(); return JSON.stringify(state); },
        async acknowledgeCareerSetback() { state.pending_career_setback = null; broadcast(); return JSON.stringify(state); },
        async clearApplicationError() { state.job_application_error = null; broadcast(); return JSON.stringify(state); },
        async buyHome(id) {
          const m = (state.housing_market || []).find(x => x.id === id);
          if (m && !(state.properties || []).some(p => p.id === id)) {
            state.money -= m.price;
            state.properties.push({ id: m.id, name: m.name, value: m.price, purchase_price: m.price });
            state.net_worth = state.money + state.properties.reduce((a, p) => a + p.value, 0);
          }
          broadcast(); return JSON.stringify(state);
        },
        async buyHomeMortgage(id) {
          const m = (state.housing_market || []).find(x => x.id === id);
          if (m && !(state.properties || []).some(p => p.id === id)) {
            const deposit = Math.round(m.price * 0.1);
            const principal = m.price - deposit;
            const payment = Math.round(principal * 0.07);
            state.money -= deposit;
            state.properties.push({ id: m.id, name: m.name, value: m.price, purchase_price: m.price, mortgage_balance: principal, mortgage_payment: payment, mortgage_rate: 0.05, mortgage_term_left: 25 });
            state.net_worth = state.money + state.properties.reduce((a, p) => a + p.value - (p.mortgage_balance || 0), 0);
          }
          broadcast(); return JSON.stringify(state);
        },
        async rentHome(id) {
          const m = (state.housing_market || []).find(x => x.id === id);
          if (m) state.rental = { id: m.id, name: m.name, rent: m.rent };
          broadcast(); return JSON.stringify(state);
        },
        async sellHome(id) {
          const p = (state.properties || []).find(x => x.id === id);
          if (p) { state.money += p.value; state.properties = state.properties.filter(x => x.id !== id); state.net_worth = state.money + state.properties.reduce((a, q) => a + q.value, 0); }
          broadcast(); return JSON.stringify(state);
        },
        async stopRenting() { state.rental = null; broadcast(); return JSON.stringify(state); },
        async setUniversityPlan(attend, major) {
          const edu = state.education;
          edu.university_intent = attend ? "attend" : "skip";
          edu.university_major = attend ? major : "";
          if (edu.awaiting_university_choice) {
            edu.awaiting_university_choice = false;
            if (attend) {
              edu.level = "University";
              edu.in_school = true;
              edu.university_name = `University of ${state.character.city}`;
            }
          }
          broadcast();
          return JSON.stringify(state);
        },
        async acknowledgeDegree() {
          state.education.degree_award_pending = false;
          broadcast();
          return JSON.stringify(state);
        },
        async dropOutUniversity() {
          state.education.in_school = false;
          state.education.university_dropped_out = true;
          broadcast();
          return JSON.stringify(state);
        },
        async answerExam() { broadcast(); return JSON.stringify(state); },
        async cheatExam() { broadcast(); return JSON.stringify(state); },
        async relationshipAction(npcId, action) {
          const rel = (state.relationships || []).find(r => r.npc_id === npcId);
          if (rel && rel.alive) {
            const delta = { talk: 3, compliment: 5, argue: -8, gift: 10 }[action] || 0;
            rel.relationship = Math.max(0, Math.min(100, rel.relationship + delta));
            if (action === "gift") state.money -= 50;
          }
          broadcast();
          return JSON.stringify(state);
        },
        async applyUniversity() {
          state.education.awaiting_university_choice = true;
          if (!state.education.admitted_tier) state.education.admitted_tier = "Community";
          broadcast();
          return JSON.stringify(state);
        },
        async enrollPostgrad(program) {
          state.education.level = program;
          state.education.in_school = true;
          broadcast();
          return JSON.stringify(state);
        },
      };
    },
  };
})();

// --------------------------------------------------------------------------
// Wire-up
// --------------------------------------------------------------------------

document.addEventListener("DOMContentLoaded", async () => {
  Icons.hydrate();

  document.getElementById("btn-random").addEventListener("click", fillRandomName);
  document.getElementById("cre-country").addEventListener("change", () => {
    refreshFlag();
    refreshCityOptions();
  });

  document.getElementById("creation-form").addEventListener("submit", (e) => {
    e.preventDefault();
    let firstName = document.getElementById("cre-first-name").value.trim();
    let lastName = document.getElementById("cre-last-name").value.trim();
    const gender = document.getElementById("cre-gender").value;
    if (!firstName) {
      const list = FALLBACK_NAMES[gender] || FALLBACK_NAMES.NonBinary;
      firstName = pickRandom(list);
    }
    if (!lastName) {
      lastName = pickRandom(FALLBACK_SURNAMES);
    }
    const country = document.getElementById("cre-country").value;
    const city = document.getElementById("cre-city").value;
    App.newGame(firstName, lastName, gender, country, city, "");
  });

  document.getElementById("btn-age-up").addEventListener("click", () => App.ageUp());
  document.getElementById("btn-restart").addEventListener("click", () => location.reload());

  document.getElementById("btn-uni-enroll").addEventListener("click", () => {
    const major = document.getElementById("university-course").value;
    App.setUniversityPlan(true, major);
  });
  document.getElementById("btn-uni-skip").addEventListener("click", () => App.setUniversityPlan(false, ""));
  document.getElementById("btn-degree-ok").addEventListener("click", () => App.acknowledgeDegree());
  document.getElementById("btn-cheat").addEventListener("click", () => {
    if (window.confirm("Are you sure you want to cheat? If you get caught you'll be thrown out of the exam.")) {
      App.cheatExam();
    }
  });

  const closeProfile = () => { App.selectedNpcId = null; App.render(); };
  document.getElementById("btn-rel-close").addEventListener("click", closeProfile);
  document.getElementById("relationship-modal").addEventListener("click", (e) => {
    if (e.target.id === "relationship-modal") closeProfile();
  });

  // Tap-anywhere-to-continue popups.
  document.getElementById("job-offer-modal").addEventListener("click", () => App.acknowledgeJobOffer());
  document.getElementById("promotion-modal").addEventListener("click", () => App.acknowledgePromotion());
  document.getElementById("job-loss-modal").addEventListener("click", () => App.acknowledgeJobLoss());
  document.getElementById("setback-modal").addEventListener("click", () => App.acknowledgeCareerSetback());

  document.querySelectorAll(".tab").forEach((el) => {
    el.addEventListener("click", () => {
      // Tapping the active tab again returns to the records page.
      App.activeTab = App.activeTab === el.dataset.tab ? "feed" : el.dataset.tab;
      App.render();
    });
  });

  await App.connect();
  App.activeTab = "feed";
  App.render();
});
