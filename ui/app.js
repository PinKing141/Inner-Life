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

const NAMES = {
  Male: ["Oliver","George","Arthur","Noah","Muhammad","Leo","Oscar","Harry","Jack","Henry"],
  Female: ["Olivia","Amelia","Isla","Ava","Ivy","Freya","Lily","Florence","Mia","Willow"],
  NonBinary: ["Alex","Jordan","Charlie","Sam","Taylor","Morgan","Casey","Riley","Quinn","Rowan"],
};
const TALENTS = ["Sports","Music","Academics","Crime","Acting"];

// --------------------------------------------------------------------------
// Bridge layer. Real Qt bridge OR a minimal in-browser fallback.
// --------------------------------------------------------------------------

const App = {
  bridge: null,
  state: null,
  activeTab: "feed",

  async connect() {
    if (typeof QWebChannel !== "undefined" && typeof qt !== "undefined") {
      await new Promise((resolve) => {
        new QWebChannel(qt.webChannelTransport, (channel) => {
          this.bridge = channel.objects.bridge;
          this.bridge.stateChanged.connect((json) => {
            this.state = JSON.parse(json);
            this.render();
          });
          resolve();
        });
      });
      const initial = await this.bridge.snapshot();
      this.state = JSON.parse(initial);
    } else {
      // Browser fallback — useful for design iteration without Qt.
      console.warn("QWebChannel not present; using mock bridge.");
      this.bridge = MockBridge.make((s) => { this.state = s; this.render(); });
      this.state = MockBridge.initial();
    }
  },

  // ---- Verb wrappers ----

  async newGame(name, gender, country, talent) {
    const result = await this.bridge.newGame(name, gender, country, talent);
    if (typeof result === "string") this.state = JSON.parse(result);
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
  },

  renderPlaying() {
    const s = this.state;
    const ch = s.character;
    const stage = stageForAge(ch.age);

    document.getElementById("hud-name").textContent = ch.name;
    document.getElementById("hud-meta").textContent = `${stage} · Age ${ch.age}`;
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

    // Panel by tab
    const panel = document.getElementById("panel");
    if (this.activeTab === "feed") panel.innerHTML = this.renderFeed();
    else if (this.activeTab === "career") panel.innerHTML = this.renderCareer();
    else if (this.activeTab === "relationships") panel.innerHTML = this.renderRelationships();
    else if (this.activeTab === "activities") panel.innerHTML = this.renderActivities();

    Icons.hydrate(panel);
    this.bindPanel(panel);

    // Tabs
    document.querySelectorAll(".tab").forEach((el) => {
      el.classList.toggle("active", el.dataset.tab === this.activeTab);
    });

    // Disable age up while an event is pending
    document.getElementById("btn-age-up").disabled = !!s.pending_event;

    // Newest entry is already rendered first (we reverse the array). Keep the
    // panel's own scroll position at the top so the latest line is visible
    // without dragging the whole page.
    if (this.activeTab === "feed") {
      panel.scrollTop = 0;
    }
  },

  renderFeed() {
    const entries = (this.state.feed || []).slice().reverse();
    return `
      <p class="panel-heading">The record</p>
      ${entries.map(e => `
        <div class="feed-entry ${e.kind}">
          <div class="feed-age">${String(e.age).padStart(2, "0")}</div>
          <div class="feed-text">${escapeHtml(e.text)}</div>
        </div>
      `).join("")}
    `;
  },

  renderCareer() {
    const s = this.state;
    const edu = s.education;
    const career = s.career;
    const jobs = s.jobs || [];

    return `
      <p class="panel-heading">Education</p>
      <div class="education-card">
        <div class="education-card-label">Current</div>
        <div class="education-card-value">${escapeHtml(edu.level)}</div>
        ${edu.in_school ? `<div class="education-card-state">Currently attending</div>` : ""}
      </div>

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
            <div class="job-row-title">${escapeHtml(j.title)}</div>
            <div class="job-row-req">Req age ${j.min_age} · smarts ${j.min_smarts}</div>
          </div>
          <div class="job-row-salary">£${(j.salary / 1000).toFixed(0)}k</div>
        </button>
      `).join("")}
    `;
  },

  renderRelationships() {
    const rels = this.state.relationships || [];
    return `
      <p class="panel-heading">Ties</p>
      ${rels.length === 0 ? `<p class="unemployed">No-one of note.</p>` : ""}
      ${rels.map(r => {
        const c = r.relationship > 70 ? "var(--good)"
                : r.relationship > 30 ? "var(--warn)"
                : "var(--bad)";
        return `
          <div class="rel-row">
            <div>
              <div class="rel-name">${escapeHtml(r.name)}</div>
              <div class="rel-kind">${escapeHtml(r.kind)}</div>
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
      <p class="panel-heading">Acts of will</p>
      <div class="activities">
        ${ACTIVITIES.map(a => `
          <button class="activity" data-action="activity" data-kind="${a.kind}">
            <span data-icon="${a.icon}"></span>
            <span class="activity-name">${a.name}</span>
            <span class="activity-cost">${a.cost}</span>
          </button>
        `).join("")}
      </div>
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
    root.querySelectorAll("[data-action='apply']").forEach((btn) => {
      btn.addEventListener("click", () => this.applyForJob(btn.dataset.job));
    });
    root.querySelectorAll("[data-action='activity']").forEach((btn) => {
      btn.addEventListener("click", () => this.activity(btn.dataset.kind));
    });
  },
};

// --------------------------------------------------------------------------
// Helpers
// --------------------------------------------------------------------------

function stageForAge(age) {
  if (age < 5) return "Baby";
  if (age < 13) return "Child";
  if (age < 18) return "Teenager";
  if (age < 65) return "Adult";
  return "Elder";
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
            <span class="country-flag">${FLAGS[c.code] || ""}</span>
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
  let state = { mode: "CREATION" };
  let pushTo = null;

  function broadcast() {
    if (pushTo) pushTo(state);
  }

  return {
    initial() { return { mode: "CREATION" }; },
    make(onChange) {
      pushTo = onChange;
      return {
        async snapshot() { return JSON.stringify(state); },
        async newGame(name, gender, country, talent) {
          state = {
            mode: "PLAYING",
            character: { name, gender, country, talent, age: 0, alive: true },
            stats: { happiness: 100, health: 90, smarts: 60, looks: 60 },
            money: 500,
            relationships: [
              { npc_id: 1, name: "Mum", kind: "Mother", relationship: 90 },
              { npc_id: 2, name: "Dad", kind: "Father", relationship: 90 },
            ],
            career: null,
            education: { level: "None", in_school: false },
            feed: [{ age: 0, text: `You were born in ${country}.`, kind: "special" }],
            pending_event: null,
            tick: 0,
            jobs: [
              { job_id: "retail",  title: "Retail Assistant", min_age: 16, min_smarts: 0, salary: 15000 },
              { job_id: "barista", title: "Barista",          min_age: 16, min_smarts: 0, salary: 16000 },
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
      };
    },
  };
})();

// --------------------------------------------------------------------------
// Wire-up
// --------------------------------------------------------------------------

document.addEventListener("DOMContentLoaded", async () => {
  Icons.hydrate();

  // Populate creation dropdowns
  buildCountryPicker();
  const talentSel = document.getElementById("cre-talent");
  TALENTS.forEach(t => talentSel.add(new Option(t, t)));

  document.getElementById("btn-random").addEventListener("click", () => {
    const g = document.getElementById("cre-gender").value;
    const list = NAMES[g] || NAMES.NonBinary;
    document.getElementById("cre-name").value = list[Math.floor(Math.random() * list.length)];
  });

  document.getElementById("creation-form").addEventListener("submit", (e) => {
    e.preventDefault();
    let name = document.getElementById("cre-name").value.trim();
    const gender = document.getElementById("cre-gender").value;
    if (!name) {
      const list = NAMES[gender] || NAMES.NonBinary;
      name = list[Math.floor(Math.random() * list.length)];
    }
    const country = document.getElementById("cre-country").value || "United Kingdom";
    const talent = document.getElementById("cre-talent").value;
    App.newGame(name, gender, country, talent);
  });

  document.getElementById("btn-age-up").addEventListener("click", () => App.ageUp());
  document.getElementById("btn-restart").addEventListener("click", () => location.reload());

  document.querySelectorAll(".tab").forEach((el) => {
    el.addEventListener("click", () => {
      App.activeTab = el.dataset.tab;
      App.render();
    });
  });

  await App.connect();
  App.activeTab = "feed";
  App.render();
});
