# Life — A Deeper Simulation

A BitLife-style life sim built on the architecture we talked through:
deterministic Python core + HTML/SVG frontend over Qt WebEngine. Same shape
as the basketball career game — Python owns the simulation, JS owns the
visuals, and they speak through a thin bridge.

## Why this structure

```
                +-----------------------+
   Player <---->|  ui/  (HTML + JS)     |     <-- the only thing the user sees
                +-----------+-----------+
                            |  QWebChannel (JSON snapshots)
                +-----------v-----------+
                |  bridge/  (Qt slots)  |     <-- thin translation layer
                +-----------+-----------+
                            |
                +-----------v-----------+
                |  controller/          |     <-- owns the current GameState
                |  - GameController     |
                +-----------+-----------+
                            |
                +-----------v-----------+
                |  core/  (pure sim)    |     <-- deterministic, no I/O
                |  - state, rng         |
                |  - sim, events        |
                |  - economy, education |
                |  - relationships      |
                |  + content/ (data)    |
                +-----------------------+
```

Layering rules (same as Fantasy Engine):

- `core/` has zero imports from `bridge/`, `controller/`, `cli/`, `ui/`.
- `core/` performs no I/O and uses no global randomness — everything routes
  through `core.rng.Rng`.
- `controller/` is the only place where save/load and timestamps live.
- `bridge/` only translates Python ↔ JSON; never embeds rules.
- `ui/` reads state, sends verbs. No simulation logic in JavaScript.

This means you can run, test, and extend the simulation entirely without Qt
— see the Rich CLI runner.

## Running

```bash
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Qt WebEngine app (the real thing)
python main.py

# Rich CLI runner (faster iteration on the sim)
python -m cli.runner

# Tests
pytest
```

## Layout

```
bitlife_deeper/
├── main.py                   # Qt entry point
├── core/                     # Deterministic simulation
│   ├── state.py              # GameState dataclass
│   ├── sim.py                # The tick (age_up) function
│   ├── rng.py                # Seeded RNG
│   ├── events.py             # Event engine
│   ├── economy.py            # Money + careers
│   ├── education.py          # Schooling lifecycle
│   ├── relationships.py      # Social graph (currently flat list)
│   └── content/              # Pure data (events, jobs, names)
├── controller/
│   └── game_controller.py    # Owns state, exposes verbs
├── bridge/
│   └── web_bridge.py         # QWebChannel slots
├── ui/                       # Vanilla HTML/CSS/JS, no build step
│   ├── index.html
│   ├── styles.css
│   ├── app.js                # Talks to Python over QWebChannel
│   └── icons.js              # Inline SVG icons (no emoji, no lucide)
├── cli/runner.py             # Rich-based terminal sim runner
└── tests/                    # Determinism + smoke tests
```

## What's already there

- Deterministic seeded sim with reproducible runs (`test_determinism.py`)
- Annual tick: education → economy → drift → events → death check
- Event engine reading from a declarative event catalogue
- Causal-chain tracking on every event choice (entry-point for a later
  LegendsReader-style narrative renderer)
- Job market with age / smarts / education gating
- Activities (study, gym, doctor, family time)
- Qt WebEngine bridge with full state broadcast
- Vanilla CSS/HTML UI, custom SVG icons, warm dark editorial palette
- In-browser mock bridge so the UI can be opened directly in a browser for
  design iteration

## What's intentionally not there yet

The current code is a *scaffold for depth*, not the depth itself. Big
systems still queued — see `docs/ROADMAP.md`.

Headline gaps:

- NPCs are stat blocks, not agents. Mum and Dad don't tick.
- No genealogy / dynasty mode.
- No social graph edges between NPCs.
- World state (era, economy, government) doesn't exist; everything happens
  in an undated present.
- Events are age-gated only — they should be state-gated too.
- Save/load is stubbed.

Each of these is a discrete extension that fits cleanly into the layering
above without architectural surgery.
