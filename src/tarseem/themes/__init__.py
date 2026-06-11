"""Built-in themes + the per-lane hue palette (05 §2, A5/A12).

A theme is a backend-neutral dict of base node/edge/title styles plus a lane
palette (hue -> row/box/label tints) used by the swimlane renderer. Only the
``default`` theme ships in the MVP core; RTL-aware named themes land in Phase 4.
"""
from __future__ import annotations

# One hue in three strengths per lane (ported from the Phase-0 swimlane spike /
# the horizontal-swimlane-diagram skill): row band, node box fill, header/label.
LANE_PALETTE: list[dict] = [
    {"row": "#E4F8F1", "box": "#C8F0E0", "label": "#269973"},  # green
    {"row": "#FFE8D6", "box": "#FFD4B0", "label": "#D97706"},  # orange
    {"row": "#E8F0FF", "box": "#D0E0FF", "label": "#1976D2"},  # blue
    {"row": "#FFF3CD", "box": "#FFE69C", "label": "#A06600"},  # yellow
]

DEFAULT_THEME: dict = {
    "name": "default",
    "palette": {"primary": "#269973", "text": "#14281D", "surface": "#FFFFFF"},
    "node": {
        "fill": "#FFFFFF",
        "border": {"color": "#333333", "width": 1, "style": "solid"},
        "text": {"color": "#14281D", "size": 12},
    },
    "edge": {"stroke": "#333333", "width": 1, "style": "solid"},
    "title": {"fill": "#269973", "text": "#FFFFFF"},
    "lanePalette": LANE_PALETTE,
}

_THEMES = {"default": DEFAULT_THEME}


def get_theme(ref: str | None = None) -> dict:
    """Return a built-in theme by ref; unknown refs fall back to default (MVP)."""
    return _THEMES.get(ref or "default", DEFAULT_THEME)


__all__ = ["DEFAULT_THEME", "LANE_PALETTE", "get_theme"]
