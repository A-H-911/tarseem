"""Sequence-diagram SVG writer (A10). Consumes a sequence ``PositionedDiagram``.

Draws the sequence chrome the shared graph writer doesn't — lifeline stems descending
from each participant head, activation bars, and call/return arrows (filled head for a
sync call, open head for a dashed return) — while reusing the shared shape/label/font
primitives. Coordinates are absolute (the layouter bakes in margins), so there is no outer
translate. Per-label direction/lang keep an RTL variant a geometry-only change later.
"""
from __future__ import annotations

from tarseem.model.ir import PositionedDiagram, PositionedEdge, PositionedNode
from tarseem.render.fonts import FONT_FAMILY, subset_woff2_datauri
from tarseem.render.svg import _arrowhead, _esc, _label_attrs, _num, _shape_svg, edge_svg_line
from tarseem.render.text import bidi_attrs, resolve_edge_corners

__all__ = ["render_sequence_svg"]

_M = 24.0
_STEM = "#9AA8A2"
_ACT_FILL = "#FFFFFF"
_ACT_BORDER = "#2E8B57"
_EDGE_DEFAULT = "#2E8B57"


def _collect_chars(diagram: PositionedDiagram) -> frozenset[str]:
    chars: set[str] = set()
    if diagram.title:
        chars.update(diagram.title)
    for n in diagram.nodes:
        chars.update(n.label.text)
    for e in diagram.edges:
        if e.label:
            chars.update(e.label.text)
    return frozenset(chars)


def _open_arrowhead(p1, p2, color: str) -> str:
    """A two-stroke 'V' open arrowhead (UML return). Horizontal segments only here."""
    (x1, _y1), (x2, y2) = p1, p2
    sz = 9.0
    d = 1.0 if x2 > x1 else -1.0
    return (
        f'<polyline points="{_num(x2 - d * sz)},{_num(y2 - sz * 0.6)} {_num(x2)},{_num(y2)} '
        f'{_num(x2 - d * sz)},{_num(y2 + sz * 0.6)}" fill="none" stroke="{color}" '
        f'stroke-width="1.5"/>'
    )


def _stem_svg(n: PositionedNode, bottom_y: float) -> str:
    cx = n.x + n.width / 2
    return (
        f'<line x1="{_num(cx)}" y1="{_num(n.y + n.height)}" x2="{_num(cx)}" '
        f'y2="{_num(bottom_y)}" stroke="{_STEM}" stroke-width="1.5" stroke-dasharray="4 4"/>'
    )


def _message_svg(e: PositionedEdge, curved: bool = True) -> list[str]:
    color = str(e.style.get("stroke", _EDGE_DEFAULT))
    sw = float(e.style.get("width", 1.5) or 1.5)
    is_return = e.style.get("style") == "dashed"
    dash = ' stroke-dasharray="6 4"' if is_return else ""
    out = [edge_svg_line(list(e.points), color, sw, dash, curved)]
    if len(e.points) >= 2:
        head = _open_arrowhead if is_return else _arrowhead
        out.append(head(e.points[-2], e.points[-1], color))
    if e.label and e.label_xy:
        lx, ly = e.label_xy
        out.append(
            f'<text x="{_num(lx)}" y="{_num(ly)}" font-size="12" fill="{color}" '
            f'{_label_attrs(e.label)}>{_esc(e.label.text)}</text>'
        )
    return out


def render_sequence_svg(diagram: PositionedDiagram) -> str:
    w, h = diagram.width, diagram.height
    bottom_y = h - _M
    b64 = subset_woff2_datauri(_collect_chars(diagram))

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{_num(w)}" height="{_num(h)}" '
        f'viewBox="0 0 {_num(w)} {_num(h)}">',
        "<style>",
        f"@font-face{{font-family:'{FONT_FAMILY}';"
        f"src:url(data:font/woff2;base64,{b64}) format('woff2');}}",
        f"text{{font-family:'{FONT_FAMILY}';}}",
        "</style>",
        f'<rect width="{_num(w)}" height="{_num(h)}" fill="#FFFFFF"/>',
    ]
    if diagram.title:
        parts.append(
            f'<text x="{_num(w / 2)}" y="{_num(_M / 2 + 6)}" font-size="18" font-weight="700" '
            f'fill="#14281D" {bidi_attrs(diagram.title)}>'
            f"{_esc(diagram.title)}</text>"
        )

    for n in diagram.nodes:  # lifeline stems first (under everything)
        parts.append(_stem_svg(n, bottom_y))
    for a in diagram.activations:  # activation bars over stems, under messages
        parts.append(
            f'<rect x="{_num(a.x)}" y="{_num(a.y)}" width="{_num(a.width)}" '
            f'height="{_num(a.height)}" fill="{_ACT_FILL}" stroke="{_ACT_BORDER}" '
            f'stroke-width="1.5"/>'
        )
    curved = resolve_edge_corners(diagram.theme)
    for e in diagram.edges:
        parts.extend(_message_svg(e, curved))
    for n in diagram.nodes:  # participant heads on top
        parts.append(_shape_svg(n))
        parts.append(
            f'<text x="{_num(n.x + n.width / 2)}" y="{_num(n.y + n.height / 2)}" '
            f'font-size="13" font-weight="600" fill="#14281D" {_label_attrs(n.label)}>'
            f"{_esc(n.label.text)}</text>"
        )

    parts.append("</svg>")
    return "\n".join(parts)
