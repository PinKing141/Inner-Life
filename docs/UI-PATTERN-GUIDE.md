# Life — UI Pack · Pattern Guide

The UI is delivered as a self-contained pack: `ui/life-ui.css` (the skin) +
`ui/life-ui.js` (the adapter). `ui/app.js` is our project's glue between the
Qt bridge and the pack.

## 1. The seam

```
┌──────────────────┐         ┌──────────────────┐
│  Python core     │         │     LifeUI       │
│  (the engine)    │ ──────▶ │  draws screens   │
│  owns numbers    │  calls  │                  │
│  owns rules      │ ◀────── │  fires events    │
└──────────────────┘         └──────────────────┘
```

**Two hard rules:**

1. The engine never touches the DOM. It only calls `LifeUI.*` setters
   (indirectly, via `ui/app.js` which translates snapshots).
2. LifeUI never runs game logic. It draws what it's handed and reports taps.

If a hand-rolled mock/shadow simulation reappears in JS, that's the same
trap we eliminated by deleting MockBridge's old shadow-sim. Don't recreate it.

## 2. The golden rule

> You do not write new CSS to add a feature. You compose primitives.

Every screen is built from the same fixed vocabulary. A new asset, a new
relationship type, a new activity, a new job — all of them are *existing
primitives with new data*.

## 3. The fixed vocabulary (9 primitives + 1 scene)

| Primitive | For | Factory |
|---|---|---|
| section | a group header | `LifeUI.section(label, count)` |
| list-item | a row | `LifeUI.item({...})` |
| meter | a 0–100 bar | `LifeUI.meter(value, color)` |
| pill | a badge | `LifeUI.pill(text, color, icon)` |
| empty | the empty state | `LifeUI.empty(message)` |
| event | a life-story entry | *(via `logEvent()`)* |
| stat | a bottom-bar stat | *(via `setStats()`)* |
| button | an action button | `LifeUI.button({...})` |
| modal | a blocking overlay | `LifeUI.modal({...})` |

Plus one scene pattern: `creation` (a full-bleed alternative to the game shell).

### list-item shape (the workhorse)

```js
{
  icon: 'house',
  accent: 'var(--c-health)',
  title: 'Two-Bed Flat',
  subtitle: 'BOUGHT 2031 · DJIBOUTI CITY',
  trailing: { ... },     // one of value/meter/badge/chevron
  locked: false,
  action: 'sell-asset',  // callback name fired on tap
  payload: assetId,
}
```

`trailing` is one of:

```js
{ kind:'value',   text:'£12,400', negative:false }
{ kind:'meter',   value:74, color:'var(--c-good)' }
{ kind:'badge',   text:'AGE 14', icon:'lock' }
{ kind:'chevron' }
```

## 4. Modal — one primitive, eight kinds

`event | offer | notice | confirm | profile | exam | picker | award` —
only the tone (icon/accent/eyebrow) changes; the body is composed of blocks.

Block types: `text`, `choices`, `deltas`, `list`, `award`, `section`, `divider`.

A choice / footer button / in-body list-item fires `'action'` to the engine
and closes the modal — unless `keepOpen:true`. The special action `'__close'`
just closes. Sequences (exam questions, profile interactions) are driven by
the engine: call `modal()` again from the action handler.

## 5. Creation — a scene driven by the engine

`LifeUI.scene('creation')` swaps in a full-bleed scene. `creationShow(step)`
renders one step at a time. Field types: `text`, `segment`, `flaggrid`,
`cards`, `list`. The engine decides the sequence (so country→city dependency
stays in the engine). On submit the UI fires `'creation-submit'` with the
collected values.

## 6. Our project's adoption

`ui/app.js` translates the Python snapshot into LifeUI calls:

- **Identity / stats** → `setIdentity` / `setStats` from `snapshot.character` and `snapshot.stats`.
- **Career, Relations, Assets, Activities screens** → `renderScreen` from snapshot lists each tick.
- **Feed** → `logEvent` for each new entry, tracked via `loggedFeedCount`.
- **Pending modals** → `pending_event_id`, `pending_job_offer`, `pending_promotion`, `pending_job_loss`, `pending_career_setback`, `job_application_error`, `exam`, `education.degree_award_pending`, `education.awaiting_university_choice` each map to one modal kind. A `currentModalKey` prevents re-raising the same modal.
- **Save/load** → topbar menu fires `'menu'`; we open a picker modal with two list-items routing to the bridge `save`/`load` slots.
- **Creation** → drives 4 JS steps (identity / origin / city / talent), then a single `bridge.newGameFull(...)` call.

### Navigation layout

Five screens registered; first four show in the nav, the fifth (assets) is
reached via a "Property & Assets" list-item on the Career screen:

```
Nav:    life · activities · [Age] · career · relations
Off-nav: assets  (reached from Career)
```

### Flags

Snapshot serves flag SVG *paths* (`country.flag_svg`). The translator wraps
each in an `<img src="…">` tag and hands it to `setIdentity({flag})` or
`flaggrid` options. The Python side never has to inline SVG content.

### Activity unlock ages

`core/activities.py` defines each activity's `UNLOCK_AGE` and exports
`list_descriptors()`. The controller adds these to the snapshot under
`activities`. The UI renders locked rows with an "Age N" badge when the
player is too young — single source of truth in core.
