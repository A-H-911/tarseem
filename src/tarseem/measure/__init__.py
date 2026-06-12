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

from tarseem.model.ir import LogicalGraph, LogicalNode, replace

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


@functools.lru_cache(maxsize=1)
def _shared_measurer() -> TextMeasurer:
    return TextMeasurer()


def measure_graph(graph: LogicalGraph, measurer: TextMeasurer | None = None) -> LogicalGraph:
    """Return a new graph whose nodes carry measured width/height. Pure: the input
    graph is left unchanged (its nodes keep ``width``/``height`` = None)."""
    m = measurer or _shared_measurer()
    sized: list[LogicalNode] = []
    for node in graph.nodes:
        if node.width is not None and node.height is not None:
            sized.append(node)
            continue
        w, h = m.node_size(node)
        sized.append(replace(node, width=w, height=h))
    return replace(graph, nodes=tuple(sized))
