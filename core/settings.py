"""User-level settings (display + accessibility + gameplay knobs).

These are app-wide, not per-character: font size carries across a
death-and-continue, contrast survives a fresh game, and a player's
preference for risk-confirmation prompts isn't tied to whichever
GameState they happen to be in. So Settings lives separately from
GameState; ``controller/settings.py`` handles the on-disk persistence
at ``~/.inner-life-settings.json``.

Validation lives here too — ``FONT_SIZES`` is the single source of
truth for the allowed values, and ``Settings.update`` enforces it so
malformed values from the UI (or a hand-edited settings file) can't
poison the snapshot.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields


# Font-size token shipped on `<html data-font-size="...">`. Three steps
# keep the picker simple; CSS scales the rest.
FONT_SIZES: tuple[str, ...] = ("small", "medium", "large")


@dataclass
class Settings:
    """Five v1 toggles. New settings get a default + a docstring here."""

    # --- Display / accessibility ------------------------------------
    # `<html data-font-size="...">` — CSS scales --base-font from it.
    font_size: str = "medium"
    # Reduced motion: drops modal/screen transitions to a fade-only
    # baseline. Toggles the `data-reduced-motion` attribute on <html>.
    reduced_motion: bool = False
    # High contrast: stronger text vs background, brighter accents.
    # Toggles `data-high-contrast` on <html>.
    high_contrast: bool = False

    # --- Gameplay quality of life -----------------------------------
    # Show a confirm modal before destructive verbs (sell home, drop
    # out, commit crime, break up). Default ON so accidental taps
    # don't undo a long run.
    confirm_risky_actions: bool = True
    # Render `+5 happiness, -3 health` annotations on feed lines that
    # came from a stat-affecting event. Useful for power users; noisy
    # for the default reader, so off by default.
    show_stat_deltas: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict | None) -> "Settings":
        """Build a Settings from a dict, ignoring unknown keys and
        falling back to defaults for missing ones. Tolerant by design
        — newer builds add fields without breaking older saves."""
        if not isinstance(data, dict):
            return cls()
        valid = {f.name for f in fields(cls)}
        kwargs = {k: v for k, v in data.items() if k in valid}
        out = cls(**kwargs)
        # Validate font_size token (the only constrained field today).
        if out.font_size not in FONT_SIZES:
            out.font_size = "medium"
        return out

    def update(self, key: str, value) -> bool:
        """Set one field with validation. Returns False if the key isn't
        recognised or the value is the wrong type / token. Doesn't
        persist — callers (controller) wire that up."""
        valid_fields = {f.name: f.type for f in fields(self)}
        if key not in valid_fields:
            return False
        # Type-correct the common cases without dragging in pydantic.
        if key == "font_size":
            if not isinstance(value, str) or value not in FONT_SIZES:
                return False
            self.font_size = value
            return True
        # All the remaining v1 fields are bools.
        # Accept JS-flavoured truthy/falsy strings for the bridge
        # round-trip (Qt slot wants typed args, so the bridge passes
        # strings — see controller/settings.py).
        if isinstance(value, bool):
            setattr(self, key, value)
            return True
        if isinstance(value, str) and value.lower() in ("true", "false"):
            setattr(self, key, value.lower() == "true")
            return True
        return False
