# Roadmap

The phases below mirror the depth conversation: each one adds a system that
multiplies replayability without doubling code complexity. Order is rough
prerequisite order, not strict.

## Phase 1 — NPC agency

The single biggest depth multiplier per unit of code. Every named character
becomes an `Agent` with stats, traits (Big Five or similar), beliefs, and
a yearly `tick()` of their own.

Touchpoints:

- New `core/agents.py` — `Agent` dataclass + tick function.
- `core.sim.age_up` calls `agents.tick_world(state, rng)` before player events.
- Existing `Relationship` becomes a thin view onto an underlying `Agent`.

The player never *sees* agent state directly; it just makes "Mum got cancer"
feel earned because there's a real model underneath.

## Phase 2 — Social graph

Edges between NPCs, not just between NPCs and player. Drama emerges from
triangles: Mum's best friend hires Dad, two friends date the same person,
a coworker recognises your sibling.

Touchpoints:

- `core/social.py` — adjacency lists per agent.
- `core/events.py` gains predicates that match on graph shape.
- Information propagation: rumours travel along edges with attenuation.

## Phase 3 — Causal narrative reader

The data is already there (every choice writes a `cause_id` into
`state.causal_chain`). What's missing is a renderer that walks the chain
and produces "you got promoted because Helen quit, and Helen quit because
her husband was transferred" without an LLM.

Direct port of Fantasy Engine's `LegendsReader`. Drop it into `core/legend.py`
and expose via the controller as a new verb (`controller.read_legend()`).

## Phase 4 — World state

The world has an era, an economy, a government. A 1962 life and a 2002 life
must feel different not because of labels but because prices, jobs, norms,
and risk profiles are different functions of world state.

Touchpoints:

- `core/world.py` — `World` dataclass, ticked alongside the player.
- `core.economy.annual_cashflow` consumes inflation/unemployment from `World`.
- New event predicates: "during a war", "during recession".

This is also where 867 AD / medieval mode could plug in (cf. Fantasy Engine).

## Phase 5 — Genealogy

Continuing as your child. Dynasties. Inherited traits, reputation, wealth,
grudges, family business.

Touchpoints:

- `Character` gains `parents`, `children`, `lineage_id`.
- New game mode: `DYNASTY` (controller-level toggle, no new screens needed
  initially — death screen offers "continue as your eldest").

## Phase 6 — State-gated events

Today events only check age. They should check state:

```python
{
  "id": "boss_wedding",
  "predicates": [Has("career"), AtLeast("stats.happiness", 40)],
  ...
}
```

Touchpoints:

- `core/predicates.py` — small DSL.
- `events.roll_event` filters by predicates before probability.

## Phase 7 — Persistence

Wire up `GameController.load` for real. JSON for human-readable saves;
optionally SQLite once the schema is stable.

## Phase 8 — Faith and culture (lifted from Fantasy Engine Phase 7)

Once world state exists, faith formation and schism pressure transfer
almost directly from Fantasy Engine. Characters inherit faith, can drift,
can convert, can lose it. Wars get a faith axis. This is the "make events
feel different by region" payoff.

---

## Cross-cutting principles

- New systems live in `core/`, never in `bridge/` or `ui/`.
- New player-facing verbs go through `GameController`, then `WebBridge`,
  then `app.js`.
- New rendered tabs need at most one render method in `App` and one CSS
  block. No template engine. No build step.
- Every new system needs at least one determinism test in `tests/`.
