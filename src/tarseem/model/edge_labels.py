"""Post-layout transform: nudge edge labels off their line (one positioned IR, many writers).

The layout stages place ``label_xy`` at the edge midpoint — *on* the line — so with a transparent
label background the line passes through the text. This pass offsets each label perpendicular to
the segment nearest it: **above** a horizontal segment, **beside** a vertical one (right for LTR,
left for RTL). Every writer (SVG, draw.io, PPTX) then reads the corrected ``label_xy``, so the fix
is uniform across formats. Idempotent: the offset is measured from the segment line, not from the
current label position, so re-running yields the same result.
"""
from __future__ import annotations

from tarseem.model.ir import PositionedDiagram, PositionedEdge, replace

__all__ = ["offset_edge_labels"]

_V_GAP = 11.0  # label sits this far above a horizontal segment (half text height + margin)


def _h_gap(text: str) -> float:
    """Half the label width + margin — places a label beside a vertical segment, clear of it."""
    return len(text) * 3.0 + 8.0


def _nearest_segment(
    points: tuple[tuple[float, float], ...], lx: float, ly: float
) -> tuple[tuple[float, float], tuple[float, float]]:
    return min(
        (((points[i], points[i + 1])) for i in range(len(points) - 1)),
        key=lambda s: ((s[0][0] + s[1][0]) / 2 - lx) ** 2 + ((s[0][1] + s[1][1]) / 2 - ly) ** 2,
    )


def _offset_xy(edge: PositionedEdge, rtl: bool) -> tuple[float, float]:
    lx, ly = edge.label_xy  # type: ignore[misc]  # guarded by caller
    (ax, ay), (bx, by) = _nearest_segment(edge.points, lx, ly)
    if abs(bx - ax) >= abs(by - ay):  # horizontal segment -> label above the line
        return (lx, (ay + by) / 2 - _V_GAP)
    line_x = (ax + bx) / 2  # vertical segment -> beside (right for LTR, left for RTL)
    gap = _h_gap(edge.label.text)  # type: ignore[union-attr]  # guarded by caller
    return (line_x - gap, ly) if rtl else (line_x + gap, ly)


def offset_edge_labels(diagram: PositionedDiagram) -> PositionedDiagram:
    """Return ``diagram`` with every labelled edge's ``label_xy`` nudged off its line."""
    rtl = diagram.direction == "RL"
    edges = tuple(
        replace(e, label_xy=_offset_xy(e, rtl))
        if (e.label and e.label_xy and len(e.points) >= 2)
        else e
        for e in diagram.edges
    )
    return replace(diagram, edges=edges)
