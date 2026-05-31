"""Event engine.

Two responsibilities:

1. Each tick (age-up), roll for a random event from the catalogue.
2. When the player picks a choice, apply its effects to state and write a
   feed entry with a `cause_id` so the causal chain stays intact.

An event may declare ``unique: True`` (the default) so it never fires twice
in the same life. Predicates further gate eligibility by state.
"""
from __future__ import annotations

from typing import Any, Optional

from core.content.events import EVENTS
from core.predicates import evaluate as evaluate_predicates
from core.causal import append_cause
from core.rng import Rng
from core.state import FeedEntry, GameState


# Sentinel-style: fields with non-serializable values (like predicates,
# which are callables / dataclass instances) must not be sent to JS.
_NON_SERIALIZABLE_KEYS = frozenset({"predicates"})


def _is_unique(event: dict) -> bool:
    """Default to unique. Only events that explicitly opt out repeat."""
    return event.get("unique", True)


def roll_event(state: GameState, rng: Rng) -> Optional[dict]:
    """Try to fire one event this tick. Returns the chosen event dict, or None.

    Filters by age window, unique-event history, and predicates (in that
    order) before rolling probability.
    """
    if state.character is None:
        return None
    age = state.character.age
    seen = set(state.fired_events)
    candidates = [
        e for e in EVENTS
        if e["min_age"] <= age <= e["max_age"]
        and not (_is_unique(e) and e["id"] in seen)
        and evaluate_predicates(e.get("predicates"), state)
    ]
    if not candidates:
        return None
    shuffled = list(candidates)
    for i in range(len(shuffled) - 1, 0, -1):
        j = rng.randint(0, i)
        shuffled[i], shuffled[j] = shuffled[j], shuffled[i]
    for e in shuffled:
        if rng.chance(e["prob"]):
            return e
    return None


def get_event(event_id: str) -> Optional[dict]:
    """Return the raw event from the catalogue (engine-internal use)."""
    for e in EVENTS:
        if e["id"] == event_id:
            return e
    return None


def get_event_for_ui(event_id: str) -> Optional[dict]:
    """Same as get_event but stripped of non-JSON-serializable fields.

    The runtime catalogue carries predicate *callables* (dataclass instances
    from core.predicates) which json.dumps cannot serialise. Anything bound
    for the bridge must go through this getter.
    """
    raw = get_event(event_id)
    if raw is None:
        return None
    return _serializable_copy(raw)


def _serializable_copy(event: dict) -> dict:
    """Shallow copy stripped of non-serializable keys (e.g. predicates)."""
    out: dict[str, Any] = {}
    for k, v in event.items():
        if k in _NON_SERIALIZABLE_KEYS:
            continue
        out[k] = v
    return out


def apply_effects(state: GameState, effects: dict) -> None:
    s = state.stats
    s.happiness += effects.get("happiness", 0)
    s.health += effects.get("health", 0)
    s.smarts += effects.get("smarts", 0)
    s.looks += effects.get("looks", 0)
    state.stats = s.clamped()
    if "money" in effects:
        state.money += effects["money"]


def _apply_side_effect(state: GameState, name: str) -> None:
    """Side-effects are non-numeric mutations (e.g. clearing a job)."""
    if name == "lose_job":
        state.career = None
    elif name == "leave_school":
        state.education.in_school = False
    elif name == "have_child":
        # Phase 5: route the birth through genealogy.have_child so the
        # child Agent, Relationship, and Character.children list all
        # update through one well-tested path. RNG forks off the event
        # tick so the same seed produces the same child.
        from core import genealogy
        rng = Rng(state.seed).fork(state.tick).fork(0xC4112D)
        note = genealogy.have_child(state, rng)
        if note:
            state.feed.append(FeedEntry(
                age=state.character.age if state.character else 0,
                text=note,
                kind="special",
                entry_id=f"feed:birth_child:{state.tick}",
            ))


def resolve_choice(state: GameState, event_id: str, choice_index: int) -> None:
    """Apply a chosen branch and log it. Records causal edges."""
    event = get_event(event_id)
    if event is None:
        return
    if choice_index < 0 or choice_index >= len(event["choices"]):
        return
    choice = event["choices"][choice_index]

    cause_id = f"event:{event_id}:{state.tick}"
    append_cause(
        state,
        node_id=cause_id,
        kind="event_choice",
        source="events.resolve_choice",
        details={
            "event_id": event_id,
            "choice": choice["text"],
            "effects": dict(choice.get("effects", {})),
            "side_effect": choice.get("side_effect"),
        },
    )

    apply_effects(state, choice.get("effects", {}))
    side = choice.get("side_effect")
    if side:
        _apply_side_effect(state, side)

    # Record this event as fired so unique events don't recur.
    if _is_unique(event) and event_id not in state.fired_events:
        state.fired_events.append(event_id)

    # Classify the feed entry by the net direction of the effects.
    eff = choice.get("effects", {})
    net = sum(v for v in eff.values() if isinstance(v, int))
    kind = "good" if net > 0 else "bad" if net < 0 else "neutral"

    state.feed.append(FeedEntry(
        age=state.character.age if state.character else 0,
        text=choice["log"],
        kind=kind,
        cause_id=cause_id,
        entry_id=f"feed:{state.tick}:{event_id}",
    ))
    state.pending_event_id = None
