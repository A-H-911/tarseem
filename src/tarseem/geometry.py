"""Shared visual constants + pure geometry math — the single source of truth for chrome.

ADR-007 has the draw.io and PPTX writers reproduce ``render/swimlane.py`` / ``render/er.py``
geometry exactly (native swimlanes can't mirror RTL headers or draw phase bands). That made the
swimlane/ER look live in three files at once, synced only by ``# MUST match`` comments. This
module is the fix ADR-007 anticipated: the constants and pure box-math both writers + the SVG
renderers + the layout layer all consume, so there is one definition, not three copies.

**Neutral leaf, on purpose.** ``layout/`` imports nothing from ``render/``/``export/``, yet it
also needs ``V_HEADER`` and ``PARALLELOGRAM_SLANT``. A root-level module that depends only on
stdlib (IR types are ``TYPE_CHECKING``-only) is importable by ``render/``, ``export/``, AND
``layout/`` without inverting the dependency graph. Functions here return coordinates only —
never emitted markup; each writer keeps its own idiom (SVG ``rx`` vs draw.io ``absoluteArcSize``
vs pptx shape-adjust).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # runtime leaf — IR types are hints only, never imported at runtime
    from tarseem.model.ir import EntityRow, LaneBand, PositionedDiagram, PositionedNode

# --- default element colours (shared by render/svg, export/drawio, export/pptx) -------------
DEFAULT_FILL = "#FFFFFF"
DEFAULT_STROKE = "#333333"
DEFAULT_TEXT = "#14281D"  # engine label colour
DEFAULT_EDGE = "#333333"

# --- swimlane chrome (render/swimlane.py, export/drawio, export/pptx; V_HEADER also layout/) --
LABEL_W = 160.0  # horizontal header-column width
V_HEADER = 64.0  # vertical-orientation lane header band height (also reserved by lanegrid)
CHIP_H = 56.0  # horizontal header-chip height
V_CHIP_H = 48.0  # vertical header-chip height
CHIP_INSET = 8.0  # chip inset from the band edge
TITLE_FILL = "#269973"
SEPARATOR = "#B0BEC5"
PHASE_FILL = "#37474F"
MARKER_BLACK = "#000000"
BADGE_R = 11.0  # auto-number badge corner-circle radius
CHROME_RADIUS = 3.0  # crisp corner for phase bands + lane-group gutters
LANE_ROW_DEFAULT = "#EEEEEE"
LANE_ACCENT_DEFAULT = "#333333"

# --- ER entity table (render/er.py, export/drawio, export/pptx) ------------------------------
ER_TITLE_FILL = "#37474F"
ER_BORDER = "#5A6B7B"
ER_ROW_SEP = "#CFD8DC"
ER_PAD_X = 10.0
ER_KEY_FILL = {"PK": "#C49000", "FK": "#3B7DD8"}

# --- UML class box (render/class_.py, export/drawio, export/pptx) ----------------------------
CLASS_TITLE_FILL = "#ECEFF1"  # light-grey name bar
CLASS_TITLE_TEXT = "#14281D"
CLASS_BORDER = "#5A6B7B"
CLASS_DIVIDER = "#90A4AE"  # line between the name / attributes / methods compartments
CLASS_PAD_X = 12.0

# --- sequence chrome (render/sequence.py, export/drawio, export/pptx) ------------------------
SEQ_MARGIN = 24.0
SEQ_STEM = "#9AA8A2"
SEQ_ACT_BORDER = "#2E8B57"

# --- shapes / edges --------------------------------------------------------------------------
PARALLELOGRAM_SLANT = 20.0  # parallelogram skew (render/svg + layout/elk + layout/lanegrid)
# Per-family default edge stroke width, so a spec's edge.style.width controls every writer
# identically (mirrors each SVG edge writer's inline default).
EDGE_WIDTH_DEFAULT = {"swimlane": 2.0, "er": 1.5, "sequence": 1.5}


# --- swimlane box math (consumed identically by swimlane/drawio/pptx) ------------------------
Rect = tuple[float, float, float, float]  # (x, y, w, h)
Point = tuple[float, float]


def chip_rect(band: LaneBand, rtl: bool, vertical: bool) -> Rect:
    """Lane header-chip rect ``(x, y, w, h)``. Sits at the top of the column (vertical) or on the
    flow-start side of the row — left for LTR, right for RTL (analysis.md §R-2)."""
    if vertical:
        return (
            band.x + CHIP_INSET,
            band.y + (V_HEADER - V_CHIP_H) / 2,
            band.width - 2 * CHIP_INSET,
            V_CHIP_H,
        )
    w = LABEL_W - 2 * CHIP_INSET
    x = (band.x + band.width - w - CHIP_INSET) if rtl else band.x + CHIP_INSET
    return (x, band.y + (band.height - CHIP_H) / 2, w, CHIP_H)


def title_bar_box(diagram: PositionedDiagram) -> Rect:
    """Swimlane title-bar rect ``(x, y, w, h)``: spans the full chrome width (group gutter through
    the last lane's right edge), sits in the top margin, and stops at the phase header (when
    phases exist) else at the first lane. Callers guard ``diagram.lanes`` non-empty."""
    lanes = diagram.lanes
    x = min([b.x for b in lanes] + [g.x for g in diagram.lane_groups])
    right = max(b.x + b.width for b in lanes)
    top = diagram.height - (lanes[-1].y + lanes[-1].height)
    bottom = diagram.phases[0].y if diagram.phases else lanes[0].y
    return (x, top, right - x, bottom - top)


@dataclass(frozen=True)
class SwimlaneChrome:
    """Shared separator geometry. ``lane_top``/``lane_bottom`` bound the lane area (used for the
    phase separators that drop through it); ``actor_p1``/``actor_p2`` are the actor/label
    separator endpoints — vertical for a horizontal swimlane, horizontal for a vertical one."""

    lane_top: float
    lane_bottom: float
    actor_p1: Point
    actor_p2: Point

    @property
    def actor_segment(self) -> tuple[Point, Point]:
        return (self.actor_p1, self.actor_p2)


def swimlane_chrome(diagram: PositionedDiagram, rtl: bool, vertical: bool) -> SwimlaneChrome:
    """Actor separator + lane span. Callers guard ``diagram.lanes`` non-empty."""
    lanes = diagram.lanes
    top = lanes[0].y
    bottom = lanes[-1].y + lanes[-1].height
    if vertical:
        sep_y = lanes[0].y + V_HEADER
        left = lanes[0].x
        right = lanes[-1].x + lanes[-1].width
        return SwimlaneChrome(top, bottom, (left, sep_y), (right, sep_y))
    m = lanes[0].x
    sep_x = (diagram.width - m - LABEL_W) if rtl else m + LABEL_W
    return SwimlaneChrome(top, bottom, (sep_x, top), (sep_x, bottom))


# --- ER / badge / pseudostate box math ------------------------------------------------------
_KEY_PILL_W = 22.0
_KEY_PILL_H = 16.0


def er_title_height(node: PositionedNode) -> float:
    """ER entity title-bar height: the first row's top offset, or the node if attribute-less."""
    return node.rows[0].y_offset if node.rows else node.height


def class_title_height(node: PositionedNode) -> float:
    """UML class name-bar height: the first member's top offset, or the node if memberless."""
    return node.members[0].y_offset if node.members else node.height


def key_pill_box(node: PositionedNode, row: EntityRow) -> Rect:
    """PK/FK pill rect ``(x, y, w, h)`` anchored to the right edge of ``row`` (vertical centre)."""
    cy = node.y + row.y_offset + row.height / 2
    x = node.x + node.width - ER_PAD_X - _KEY_PILL_W
    return (x, cy - _KEY_PILL_H / 2, _KEY_PILL_W, _KEY_PILL_H)


def badge_center(node: PositionedNode, side: str) -> Point:
    """Auto-number badge circle centre — the node's top-right corner (``side == "right"``) or
    top-left (RTL default)."""
    cx = node.x + node.width if side == "right" else node.x
    return (cx, node.y)


@dataclass(frozen=True)
class Pseudostate:
    """State-machine initial/final pseudostate circle geometry. ``inner_r`` is the final dot."""

    cx: float
    cy: float
    r: float
    inner_r: float


def pseudostate_circles(node: PositionedNode) -> Pseudostate:
    r = min(node.width, node.height) / 2
    return Pseudostate(node.x + node.width / 2, node.y + node.height / 2, r, r * 0.5)
