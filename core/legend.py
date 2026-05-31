"""Causal narrative reader.

Builds a deterministic, human-readable explanation chain from entries in
``GameState.causal_chain`` and feed entries linked via ``cause_id``.
"""
from __future__ import annotations

from dataclasses import dataclass

from core.state import GameState


@dataclass(frozen=True)
class LegendOptions:
    max_depth: int = 6
    max_items: int = 8


def _label_for(node: dict) -> str:
    kind = node.get("kind", "")
    if kind == "event_choice":
        raw_details = node.get("details")
        details = raw_details if isinstance(raw_details, dict) else {}
        event_id = details.get("event_id") or node.get("event_id", "event")
        choice = details.get("choice") or node.get("choice", "")
        if choice:
            return f"{event_id}: {choice}"
        return event_id
    return str(node.get("id", "cause"))


def read_legend(state: GameState, target_entry_id: str | None = None, *, options: LegendOptions | None = None) -> dict:
    """Return a narrative explanation for a feed entry.

    The returned dict is JSON-serialisable and safe for the bridge/UI.
    """
    opts = options or LegendOptions()
    feed = state.feed or []
    if not feed:
        return {
            "target_entry_id": None,
            "target_text": "",
            "summary": "No life records yet.",
            "items": [],
        }

    target = None
    if target_entry_id:
        target = next((f for f in feed if f.entry_id == target_entry_id), None)
    if target is None:
        # Prefer latest entry with an attached cause.
        target = next((f for f in reversed(feed) if f.cause_id), feed[-1])

    idx = {c.get("id"): c for c in state.causal_chain if isinstance(c, dict) and c.get("id")}

    items: list[dict] = []
    seen: set[str] = set()
    current_id = target.cause_id
    depth = 0

    while current_id and depth < opts.max_depth and current_id not in seen:
        seen.add(current_id)
        node = idx.get(current_id)
        if node is None:
            items.append({
                "id": current_id,
                "depth": depth,
                "label": current_id,
                "kind": "unknown",
            })
            break

        items.append({
            "id": current_id,
            "depth": depth,
            "label": _label_for(node),
            "kind": node.get("kind", "unknown"),
            "tick": node.get("tick"),
            "event_id": (node.get("details", {}) or {}).get("event_id", node.get("event_id")),
            "parent_id": node.get("parent_id"),
            "schema_version": node.get("schema_version"),
            "source": node.get("source"),
        })
        current_id = node.get("parent_id")
        depth += 1

    items = items[: opts.max_items]
    if items:
        summary = f"{target.text} This traces back through {len(items)} recorded cause step(s)."
    else:
        summary = f"{target.text} No explicit cause chain was recorded for this moment."

    return {
        "target_entry_id": target.entry_id,
        "target_text": target.text,
        "target_age": target.age,
        "summary": summary,
        "items": items,
    }
