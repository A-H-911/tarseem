"""Built-in themes + the per-lane hue palette (05 §2, A5/A12, F4).

A theme is a backend-neutral dict of base node/edge/title styles, a ``lanePalette``
(hue -> row/box/label tints used by the swimlane renderer), and a ``fontStack`` (family
fallback chain; the embedded Cairo subset is always first so it wins regardless). Themes
are **direction-independent**: RTL mirrors geometry only (header side, badge corner, flow),
so the same theme drives LTR and RTL diagrams unchanged (analysis.md §Reference-2).

Phase 4 ships three: ``default`` (green), ``corporate`` (blue/slate), ``monochrome``
(grayscale). They share identical geometry and differ only by palette + title fill —
demonstrating that the theme is a swappable function over invariant geometry (F4).
"""
from __future__ import annotations

__all__ = [
    "DEFAULT_THEME",
    "CORPORATE_THEME",
    "MONOCHROME_THEME",
    "LANE_PALETTE",
    "FONT_STACK",
    "get_theme",
    "theme_names",
]

# The renderer always embeds a used-glyph subset under the family ``TarseemCairo``; it is
# listed first so it wins. The rest are graceful fallbacks for non-embedding consumers
# (e.g. draw.io / textAsPaths metadata). Cairo + Noto Sans Arabic both carry full Arabic.
FONT_STACK: list[str] = [
    "TarseemCairo",
    "Cairo",
    "Noto Sans Arabic",
    "Noto Sans",
    "sans-serif",
]

# One hue in three strengths per lane (ported from the Phase-0 swimlane spike /
# the horizontal-swimlane-diagram skill): row band, node box fill, header/label.
LANE_PALETTE: list[dict] = [
    {"row": "#E4F8F1", "box": "#C8F0E0", "label": "#269973"},  # green
    {"row": "#FFE8D6", "box": "#FFD4B0", "label": "#D97706"},  # orange
    {"row": "#E8F0FF", "box": "#D0E0FF", "label": "#1976D2"},  # blue
    {"row": "#FFF3CD", "box": "#FFE69C", "label": "#A06600"},  # yellow
]

# Corporate: cool blue/slate/teal/violet family; bright-blue title bar.
_CORPORATE_PALETTE: list[dict] = [
    {"row": "#E8F0FE", "box": "#C6DAFC", "label": "#1A56DB"},  # blue
    {"row": "#EEF2F6", "box": "#D5DCE5", "label": "#475569"},  # slate
    {"row": "#E6F4F1", "box": "#C2E4DC", "label": "#0E7C66"},  # teal
    {"row": "#F0ECFB", "box": "#DAD0F5", "label": "#6D28D9"},  # violet
]

# Monochrome: full grayscale; near-black title bar. Same geometry, swapped palette.
_MONOCHROME_PALETTE: list[dict] = [
    {"row": "#F4F4F5", "box": "#E0E0E2", "label": "#3F3F46"},
    {"row": "#ECECEE", "box": "#D4D4D8", "label": "#27272A"},
    {"row": "#E4E4E7", "box": "#C8C8CD", "label": "#52525B"},
    {"row": "#F0F0F2", "box": "#D9D9DE", "label": "#18181B"},
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
    "fontStack": FONT_STACK,
}

CORPORATE_THEME: dict = {
    "name": "corporate",
    "palette": {"primary": "#1A56DB", "text": "#1E293B", "surface": "#FFFFFF"},
    "node": {
        "fill": "#FFFFFF",
        "border": {"color": "#475569", "width": 1, "style": "solid"},
        "text": {"color": "#1E293B", "size": 12},
    },
    "edge": {"stroke": "#475569", "width": 1, "style": "solid"},
    "title": {"fill": "#1A56DB", "text": "#FFFFFF"},
    "lanePalette": _CORPORATE_PALETTE,
    "fontStack": FONT_STACK,
}

MONOCHROME_THEME: dict = {
    "name": "monochrome",
    "palette": {"primary": "#1F2937", "text": "#18181B", "surface": "#FFFFFF"},
    "node": {
        "fill": "#FFFFFF",
        "border": {"color": "#3F3F46", "width": 1, "style": "solid"},
        "text": {"color": "#18181B", "size": 12},
    },
    "edge": {"stroke": "#3F3F46", "width": 1, "style": "solid"},
    "title": {"fill": "#1F2937", "text": "#FFFFFF"},
    "lanePalette": _MONOCHROME_PALETTE,
    "fontStack": FONT_STACK,
}

_THEMES: dict[str, dict] = {
    "default": DEFAULT_THEME,
    "corporate": CORPORATE_THEME,
    "monochrome": MONOCHROME_THEME,
}


def get_theme(ref: str | None = None) -> dict:
    """Return a built-in theme by ref/name; unknown refs fall back to default."""
    return _THEMES.get(ref or "default", DEFAULT_THEME)


def theme_names() -> list[str]:
    """Names of the built-in themes (for ``tarseem themes`` / docs)."""
    return list(_THEMES)
