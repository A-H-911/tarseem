"""Text measurement service (ADR-004, FR-4): shaped advances BEFORE layout.

uharfbuzz shapes each label with the *bundled* font and reports the true advance
width, so node boxes are sized to their content before ELK ever positions them. The
same call path handles Arabic (``guess_segment_properties`` sets rtl + script), which
is why measurement — not the renderer — owns sizing. Latin is exercised in the MVP;
the Arabic path is identical and validated by spike 2.
"""
from __future__ import annotations

import functools
from pathlib import Path

import uharfbuzz as hb

from tarseem.model.ir import EntityRow, LogicalGraph, LogicalNode, replace

__all__ = ["TextMeasurer", "measure_graph", "default_font_path"]

# Box sizing constants (px). Diamonds inscribe their label, so they need extra room.
_PAD_X = 18.0
_PAD_Y = 14.0
_MIN_W = 84.0
_MIN_H = 44.0
_DIAMOND_SCALE = 1.6
_DEFAULT_SIZE = 12.0
# State-machine pseudostates are fixed-size markers, not text boxes (FR family: state).
_STATE_MARKER = {"initial": 26.0, "final": 30.0}
_CUBE_DEPTH = 14.0  # deployment 3D-node faces eat into the box; pad so the label still fits
# ER entity table geometry (family: er). Title row + fixed-height attribute rows.
_ER_TITLE_H = 30.0
_ER_ROW_H = 24.0
_ER_PAD_X = 14.0
_ER_KEY_W = 30.0  # right-side room for a PK/FK tag

_FONTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"


def default_font_path() -> Path:
    """Absolute path to the bundled default font (Cairo, OFL). Never a system font."""
    return _FONTS_DIR / "Cairo-VF.ttf"


class TextMeasurer:
    """Measures shaped text width with a single cached HarfBuzz face."""

    def __init__(self, font_path: Path | None = None) -> None:
        self._font_path = font_path or default_font_path()
        blob = hb.Blob.from_file_path(str(self._font_path))
        self._face = hb.Face(blob)
        self._upem = self._face.upem

    @functools.lru_cache(maxsize=4096)  # noqa: B019 - measurer instances are long-lived
    def width(self, text: str, size: float) -> float:
        """Shaped advance width of ``text`` at ``size`` px (0 for empty)."""
        if not text:
            return 0.0
        font = hb.Font(self._face)
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()  # direction (rtl for Arabic) + script + language
        hb.shape(font, buf)
        advance_units = sum(p.x_advance for p in buf.glyph_positions)
        return advance_units / self._upem * size

    def node_size(self, node: LogicalNode) -> tuple[float, float]:
        if node.shape in _STATE_MARKER:  # initial/final pseudostates: fixed-size markers
            d = _STATE_MARKER[node.shape]
            return d, d
        size = float((node.style.get("text") or {}).get("size", _DEFAULT_SIZE))
        text_w = self.width(node.label.text, size)
        w = max(text_w + 2 * _PAD_X, _MIN_W)
        h = max(size + 2 * _PAD_Y, _MIN_H)
        if node.shape == "diamond":
            w *= _DIAMOND_SCALE
            h *= _DIAMOND_SCALE
        elif node.shape == "cube":  # reserve room for the 3D depth faces
            w += _CUBE_DEPTH
            h += _CUBE_DEPTH
        return round(w, 2), round(h, 2)

    def table_size(
        self, node: LogicalNode
    ) -> tuple[float, float, tuple[EntityRow, ...]]:
        """Size an ER entity table and stamp each row's vertical geometry (y_offset/height).

        Width fits the title and the widest attribute row (plus a key tag when any row has
        one); height is the title row plus one fixed-height row per attribute."""
        size = float((node.style.get("text") or {}).get("size", _DEFAULT_SIZE))
        title_w = self.width(node.label.text, size)
        row_w = max((self.width(r.label.text, size) for r in node.rows), default=0.0)
        has_key = any(r.key for r in node.rows)
        content_w = max(title_w, row_w + (_ER_KEY_W if has_key else 0.0))
        w = max(content_w + 2 * _ER_PAD_X, _MIN_W)
        h = _ER_TITLE_H + len(node.rows) * _ER_ROW_H
        rows = tuple(
            replace(r, y_offset=_ER_TITLE_H + i * _ER_ROW_H, height=_ER_ROW_H)
            for i, r in enumerate(node.rows)
        )
        return round(w, 2), round(h, 2), rows


@functools.lru_cache(maxsize=1)
def _shared_measurer() -> TextMeasurer:
    return TextMeasurer()


def measure_graph(graph: LogicalGraph, measurer: TextMeasurer | None = None) -> LogicalGraph:
    """Return a new graph whose nodes carry measured width/height. Pure: the input
    graph is left unchanged (its nodes keep ``width``/``height`` = None).

    Opt-in ``layout.uniformNodeSize`` then snaps box nodes to a common size (so e.g. two
    result boxes render identically). Off by default — output is unchanged."""
    m = measurer or _shared_measurer()
    sized: list[LogicalNode] = []
    for node in graph.nodes:
        if node.width is not None and node.height is not None:
            sized.append(node)
            continue
        if node.rows:  # ER entity table: size from rows + stamp per-row geometry
            w, h, rows = m.table_size(node)
            sized.append(replace(node, width=w, height=h, rows=rows))
            continue
        w, h = m.node_size(node)
        sized.append(replace(node, width=w, height=h))
    graph = replace(graph, nodes=tuple(sized))
    uniform = graph.layout_options.get("uniformNodeSize")
    if uniform:
        graph = _apply_uniform_size(graph, uniform)
    return graph


def _apply_uniform_size(graph: LogicalGraph, uniform: bool | str | dict) -> LogicalGraph:
    """Snap box nodes to a uniform size (FR-5.x, opt-in). ``uniformNodeSize`` may be ``true``
    (all eligible nodes share max W x max H), ``"byShape"`` (uniform within each shape), or
    ``{scope, width?, height?}`` for explicit dims. ER tables and fixed pseudostate markers
    are exempt (their size is content/semantics-driven)."""
    if isinstance(uniform, dict):
        scope = str(uniform.get("scope", "all"))
        fixed_w, fixed_h = uniform.get("width"), uniform.get("height")
    else:
        scope = "byShape" if uniform == "byShape" else "all"
        fixed_w = fixed_h = None
    eligible = [
        n for n in graph.nodes
        if not n.rows and n.shape not in _STATE_MARKER and n.width is not None
    ]
    if not eligible:
        return graph
    elig_ids = {n.id for n in eligible}
    global_w = max(n.width for n in eligible if n.width is not None)
    global_h = max(n.height for n in eligible if n.height is not None)
    shape_max: dict[str, tuple[float, float]] = {}
    for n in eligible:
        pw, ph = shape_max.get(n.shape, (0.0, 0.0))
        shape_max[n.shape] = (max(pw, n.width or 0.0), max(ph, n.height or 0.0))
    out: list[LogicalNode] = []
    for n in graph.nodes:
        if n.id not in elig_ids:
            out.append(n)
            continue
        if scope == "byShape":
            w, h = shape_max[n.shape]
        else:
            w, h = global_w, global_h
        if fixed_w is not None:
            w = float(fixed_w)
        if fixed_h is not None:
            h = float(fixed_h)
        out.append(replace(n, width=round(w, 2), height=round(h, 2)))
    return replace(graph, nodes=tuple(out))
