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

# --- sequence chrome (render/sequence.py, export/drawio, export/pptx) ------------------------
SEQ_MARGIN = 24.0
SEQ_STEM = "#9AA8A2"
SEQ_ACT_BORDER = "#2E8B57"

# --- shapes / edges --------------------------------------------------------------------------
PARALLELOGRAM_SLANT = 20.0  # parallelogram skew (render/svg + layout/elk + layout/lanegrid)
# Per-family default edge stroke width, so a spec's edge.style.width controls every writer
# identically (mirrors each SVG edge writer's inline default).
EDGE_WIDTH_DEFAULT = {"swimlane": 2.0, "er": 1.5, "sequence": 1.5}
