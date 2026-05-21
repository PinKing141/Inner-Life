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
const TALENTS = ["Sports","Music","Academics","Crime","Acting"];
const STAGE_ICONS = { Infant: "infant", School: "school", Teenager: "school", Career: "briefcase" };
const DATA_BASE = "flags-svg";

// How many recent feed entries to render. 100 years of play used to be one
// unbounded list — the UI would lag in late game. 30 is plenty for context.
const FEED_VISIBLE = 30;

const App = {
  bridge: null,
  state: null,
  activeTab: "feed",
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
    this.renderUniversityModal();
    this.renderDegreeModal();
  },

  renderUniversityModal() {
    const modal = document.getElementById("university-modal");
    if (!modal) return;
    const edu = this.state.education;
    const show = this.state.mode === "PLAYING" && edu && edu.awaiting_university_choice && !this.state.pending_event;
    modal.classList.toggle("hidden", !show);
    if (!show) return;

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
    document.getElementById("degree-text").textContent =
      `You earned your undergraduate degree in ${major} from ${uni}!`;
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

    document.getElementById("btn-age-up").disabled =
      !!s.pending_event ||
      !!(s.education && (s.education.awaiting_university_choice || s.education.degree_award_pending));

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

      <p class="panel-heading">Career</p>
      ${career ? `
        <div class="current-job">
          <div class="current-job-label">Current role</div>
          <div class="current-job-title">${escapeHtml(career.title)}</div>
          <div class="current-job-meta">Salary £${career.salary.toLocaleString()} / yr</div>
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
          <div class="rel-row${r.alive ? "" : " deceased"}">
            <div>
              <div class="rel-name">${escapeHtml(r.name)}</div>
              <div class="rel-kind">${escapeHtml(kindLabel)}</div>
            </div>
            <div class="rel-bar">
              <div class="rel-bar-fill" style="width:${r.relationship}%;background:${c}"></div>
            </div>
          </div>
        `;
      }).join("")}
    `;
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
    const career = this.state.career;
    const income = career ? career.salary : 0;
    const expenses = 0;
    const debt = (this.state.education && this.state.education.student_debt) || 0;
    return `
      <p class="panel-heading">Assets</p>
      <div class="education-card">
        <div class="education-card-label">Income</div>
        <div class="education-card-value">£${income.toLocaleString()} / yr</div>
      </div>
      <div class="education-card">
        <div class="education-card-label">Expenses</div>
        <div class="education-card-value">£${expenses.toLocaleString()} / yr</div>
      </div>
      ${debt > 0 ? `
      <div class="education-card">
        <div class="education-card-label">Student debt</div>
        <div class="education-card-value">£${debt.toLocaleString()}</div>
      </div>` : ""}
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
      btn.addEventListener("click", () => this.applyForJob(btn.dataset.job));
    });
    root.querySelectorAll("[data-action='activity']").forEach((btn) => {
      btn.addEventListener("click", () => this.activity(btn.dataset.kind));
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

    const talentSel = document.getElementById("cre-talent");
    talentSel.innerHTML = "";
    TALENTS.forEach((t) => talentSel.add(new Option(t, t)));

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
            agents: [],
            career: null,
            education: {
              level: "None", in_school: false, university_intent: "undecided",
              university_major: "", university_name: "", degree_field: "",
              degree_completed: false, student_debt: 0,
              awaiting_university_choice: false, degree_award_pending: false,
            },
            courses: MOCK_COURSES,
            feed: [{ age: 0, text: `You were born in ${city || cn.cities[0]}, ${cn.name}.`, kind: "special" }],
            pending_event: null,
            tick: 0,
            country_flag: cn.flag,
            country_flag_svg: cn.flag_svg,
            country_code: cn.code,
            currency: cn.currency,
            countries: MOCK_COUNTRIES,
            jobs: [
              { job_id: "retail",  title: "Retail Assistant", min_age: 16, min_smarts: 0, salary: 15000, track: "general" },
              { job_id: "barista", title: "Barista",          min_age: 16, min_smarts: 0, salary: 16000, track: "general" },
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
        async applyForJob() { broadcast(); return JSON.stringify(state); },
        async activity() { broadcast(); return JSON.stringify(state); },
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
    const talent = document.getElementById("cre-talent").value;
    App.newGame(firstName, lastName, gender, country, city, talent);
  });

  document.getElementById("btn-age-up").addEventListener("click", () => App.ageUp());
  document.getElementById("btn-restart").addEventListener("click", () => location.reload());

  document.getElementById("btn-uni-enroll").addEventListener("click", () => {
    const major = document.getElementById("university-course").value;
    App.setUniversityPlan(true, major);
  });
  document.getElementById("btn-uni-skip").addEventListener("click", () => App.setUniversityPlan(false, ""));
  document.getElementById("btn-degree-ok").addEventListener("click", () => App.acknowledgeDegree());

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
