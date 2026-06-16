"""UML class-diagram SVG writer (family: class). Consumes an ELK-laid PositionedDiagram.

Each node is a class box: a name bar plus attribute and method compartments separated by
divider lines, drawn from the per-member geometry the measurement stage stamped onto each
``ClassMember`` (mirrors ``render/er.py``). Relationship edges are orthogonal connectors with
generic routing; this writer only draws them + their labels. Per-label direction/lang keeps
Arabic first-class (geometry-only RTL).
"""
from __future__ import annotations

from tarseem.geometry import (
    CLASS_BORDER as _BORDER,
    CLASS_DIVIDER as _DIVIDER,
    CLASS_PAD_X as _PAD_X,
    CLASS_TITLE_FILL as _TITLE_FILL,
    CLASS_TITLE_TEXT as _TITLE_TEXT,
    class_title_height,
)
from tarseem.model.ir import PositionedDiagram, PositionedEdge, PositionedNode
from tarseem.render.fonts import FONT_FAMILY, subset_woff2_datauri
from tarseem.render.svg import _arrowhead, _esc, _num, edge_svg_line
from tarseem.render.text import label_attrs, resolve_edge_corners

__all__ = ["render_class_svg"]

_MARGIN = 24.0
_BODY_FILL = "#FFFFFF"
_MEMBER_TEXT = "#14281D"
_EDGE_DEFAULT = "#5A6B7B"


def _collect_chars(diagram: PositionedDiagram) -> frozenset[str]:
    chars: set[str] = set()
    for n in diagram.nodes:
        chars.update(n.label.text)
        for m in n.members:
            chars.update(m.label.text)
    for e in diagram.edges:
        if e.label:
            chars.update(e.label.text)
    return frozenset(chars)


def _class_box(n: PositionedNode) -> list[str]:
    """A class box: square outer rect, a filled name bar, then member lines with a divider
    above the first member of each group (attributes, then methods)."""
    x, y, w, h = n.x, n.y, n.width, n.height
    title_h = class_title_height(n)
    parts = [
        f'<rect x="{_num(x)}" y="{_num(y)}" width="{_num(w)}" height="{_num(h)}" '
        f'fill="{_BODY_FILL}" stroke="{_BORDER}" stroke-width="1.5"/>',
        f'<rect x="{_num(x)}" y="{_num(y)}" width="{_num(w)}" height="{_num(title_h)}" '
        f'fill="{_TITLE_FILL}"/>',
        f'<text x="{_num(x + w / 2)}" y="{_num(y + title_h / 2)}" font-size="13" '
        f'font-weight="700" fill="{_TITLE_TEXT}" {label_attrs(n.label)}>'
        f"{_esc(n.label.text)}</text>",
    ]
    prev_group: str | None = None
    for m in n.members:
        my = y + m.y_offset
        if m.group != prev_group:  # divider above the first member of each compartment group
            parts.append(
                f'<line x1="{_num(x)}" y1="{_num(my)}" x2="{_num(x + w)}" y2="{_num(my)}" '
                f'stroke="{_DIVIDER}" stroke-width="1"/>'
            )
            prev_group = m.group
        parts.append(
            f'<text x="{_num(x + _PAD_X)}" y="{_num(my + m.height / 2)}" font-size="12" '
            f'fill="{_MEMBER_TEXT}" {label_attrs(m.label, anchor="start")}>'
            f"{_esc(m.label.text)}</text>"
        )
    return parts


def _edge_svg(e: PositionedEdge, curved: bool = True) -> list[str]:
    color = str(e.style.get("stroke", _EDGE_DEFAULT))
    sw = float(e.style.get("width", 1.5) or 1.5)
    dash = ' stroke-dasharray="6 4"' if e.style.get("style") == "dashed" else ""
    out = [edge_svg_line(list(e.points), color, sw, dash, curved)]
    if len(e.points) >= 2:
        out.append(_arrowhead(e.points[-2], e.points[-1], color))
    if e.label and e.label_xy:
        lx, ly = e.label_xy
        out.append(
            f'<text x="{_num(lx)}" y="{_num(ly)}" font-size="11" fill="{color}" '
            f"{label_attrs(e.label)}>{_esc(e.label.text)}</text>"
        )
    return out


def render_class_svg(diagram: PositionedDiagram) -> str:
    w = diagram.width + 2 * _MARGIN
    h = diagram.height + 2 * _MARGIN
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
        f'<g transform="translate({_num(_MARGIN)},{_num(_MARGIN)})">',
    ]
    curved = resolve_edge_corners(diagram.theme)
    for e in diagram.edges:  # connectors under boxes so arrowheads tuck at the border
        parts.extend(_edge_svg(e, curved))
    for n in diagram.nodes:
        parts.extend(_class_box(n))
    parts.append("</g>")
    parts.append("</svg>")
    return "\n".join(parts)
