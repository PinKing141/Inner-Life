# Architecture

## Data flow per tick

```
                          USER CLICKS "AGE UP"
                                    │
                                    ▼
                       ui/app.js   App.ageUp()
                                    │
                                    ▼ JS → Python (QWebChannel)
                       bridge/   WebBridge.ageUp()
                                    │
                                    ▼
                  controller/   GameController.age_up()
                                    │
                                    ▼
                        core/   sim.age_up(state)
                              │   │   │   │   │
              ┌───────────────┘   │   │   │   └────────────────┐
              ▼                   ▼   ▼   ▼                    ▼
       education.tick    economy.cashflow    relationships.drift    events.roll
              │                   │   │   │                    │
              └───────────────────┴───┴───┴────────────────────┘
                                    │
                                    ▼
                       state mutated in place
                                    │
                                    ▼
                  controller broadcasts snapshot
                                    │
                                    ▼ Python → JS (stateChanged signal)
                      ui/app.js   App.render()  ← re-renders from snapshot
```

## Layering rule

Imports point only **downward** in this diagram:

```
ui   ───►   bridge   ───►   controller   ───►   core
                                                  │
                                                  ▼
                                            core/content
```

If anything in `core/` imports from `bridge/`, `controller/`, or `ui/`, the
build is broken. The tests in `tests/test_determinism.py` will not catch
this directly, but the Rich CLI will: `python -m cli.runner` should always
work without PySide6 installed beyond the import in `main.py` and `bridge/`.

## State as the single source of truth

UI never holds derived game state. It holds:

- the active tab (a UI concern, not a game concern)
- a copy of the most recent snapshot, used purely for rendering

Every player action goes Python → Python → broadcast → UI re-render. This
is what makes the system deterministic and what lets the Rich CLI and the
Qt UI share 100% of their game logic.
