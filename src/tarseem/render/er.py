"""ER entity-relationship SVG writer (family: er). Consumes an ELK-laid PositionedDiagram.

Each entity is a table: a coloured title row plus one row per attribute (with an optional
PK/FK key tag), drawn from the per-row geometry the measurement stage stamped onto each
``EntityRow``. Relationship edges are orthogonal connectors that the layout adapter has
already anchored to specific attribute rows; this writer only draws them + their cardinality
labels. Per-label direction/lang keeps Arabic first-class (geometry-only RTL).
"""
from __future__ import annotations

from tarseem.model.ir import PositionedDiagram, PositionedEdge, PositionedNode
from tarseem.render.fonts import FONT_FAMILY, subset_woff2_datauri
from tarseem.render.svg import _arrowhead, _esc, _num
from tarseem.render.text import label_attrs

__all__ = ["render_er_svg"]

_MARGIN = 24.0
_TITLE_FILL = "#37474F"
_TITLE_TEXT = "#FFFFFF"
_BORDER = "#5A6B7B"
_ROW_FILL = "#FFFFFF"
_ROW_SEP = "#CFD8DC"
_EDGE_DEFAULT = "#5A6B7B"
_PAD_X = 10.0
_KEY_FILL = {"PK": "#C49000", "FK": "#3B7DD8"}


def _collect_chars(diagram: PositionedDiagram) -> frozenset[str]:
    chars: set[str] = set("PKF")  # key tags
    for n in diagram.nodes:
        chars.update(n.label.text)
        for r in n.rows:
            chars.update(r.label.text)
    for e in diagram.edges:
        if e.label:
            chars.update(e.label.text)
    return frozenset(chars)


def _key_tag(key: str, x_right: float, cy: float) -> list[str]:
    """A small PK/FK pill anchored to the right edge of a row."""
    fill = _KEY_FILL.get(key, "#777777")
    tw = 22.0
    tx = x_right - _PAD_X - tw
    return [
        f'<rect x="{_num(tx)}" y="{_num(cy - 8)}" width="{_num(tw)}" height="16" rx="3" '
        f'fill="{fill}"/>',
        f'<text x="{_num(tx + tw / 2)}" y="{_num(cy)}" font-size="10" font-weight="700" '
        f'fill="#FFFFFF" text-anchor="middle" dominant-baseline="central">{_esc(key)}</text>',
    ]


def _entity(n: PositionedNode) -> list[str]:
    x, y, w, h = n.x, n.y, n.width, n.height
    title_h = n.rows[0].y_offset if n.rows else h
    parts = [
        f'<rect x="{_num(x)}" y="{_num(y)}" width="{_num(w)}" height="{_num(h)}" rx="6" '
        f'fill="{_ROW_FILL}" stroke="{_BORDER}" stroke-width="1.5"/>',
        # title bar (clip the rounded top by overdrawing a filled rect with rounded top only)
        f'<path d="M {_num(x)} {_num(y + title_h)} L {_num(x)} {_num(y + 6)} '
        f'Q {_num(x)} {_num(y)} {_num(x + 6)} {_num(y)} L {_num(x + w - 6)} {_num(y)} '
        f'Q {_num(x + w)} {_num(y)} {_num(x + w)} {_num(y + 6)} '
        f'L {_num(x + w)} {_num(y + title_h)} Z" fill="{_TITLE_FILL}"/>',
        f'<text x="{_num(x + w / 2)}" y="{_num(y + title_h / 2)}" font-size="13" '
        f'font-weight="700" fill="{_TITLE_TEXT}" {label_attrs(n.label)}>'
        f"{_esc(n.label.text)}</text>",
    ]
    for r in n.rows:
        ry = y + r.y_offset
        cy = ry + r.height / 2
        parts.append(
            f'<line x1="{_num(x)}" y1="{_num(ry)}" x2="{_num(x + w)}" y2="{_num(ry)}" '
            f'stroke="{_ROW_SEP}" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{_num(x + _PAD_X)}" y="{_num(cy)}" font-size="12" fill="#14281D" '
            f'{label_attrs(r.label, anchor="start")}>{_esc(r.label.text)}</text>'
        )
        if r.key:
            parts.extend(_key_tag(r.key, x + w, cy))
    return parts


def _edge_svg(e: PositionedEdge) -> list[str]:
    color = str(e.style.get("stroke", _EDGE_DEFAULT))
    sw = float(e.style.get("width", 1.5) or 1.5)
    dash = ' stroke-dasharray="6 4"' if e.style.get("style") == "dashed" else ""
    poly = " ".join(f"{_num(px)},{_num(py)}" for px, py in e.points)
    out = [
        f'<polyline points="{poly}" fill="none" stroke="{color}" '
        f'stroke-width="{_num(sw)}"{dash}/>'
    ]
    if len(e.points) >= 2:
        out.append(_arrowhead(e.points[-2], e.points[-1], color))
    if e.label and e.label_xy:
        lx, ly = e.label_xy
        half = max(10.0, len(e.label.text) * 3.6)
        out.append(
            f'<rect x="{_num(lx - half)}" y="{_num(ly - 9)}" width="{_num(2 * half)}" '
            f'height="18" fill="#FFFFFF" opacity="0.9"/>'
        )
        out.append(
            f'<text x="{_num(lx)}" y="{_num(ly)}" font-size="11" fill="{color}" '
            f'{label_attrs(e.label)}>{_esc(e.label.text)}</text>'
        )
    return out


def render_er_svg(diagram: PositionedDiagram) -> str:
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
    for e in diagram.edges:  # connectors under entities so arrowheads tuck at the border
        parts.extend(_edge_svg(e))
    for n in diagram.nodes:
        parts.extend(_entity(n))
    parts.append("</g>")
    parts.append("</svg>")
    return "\n".join(parts)
