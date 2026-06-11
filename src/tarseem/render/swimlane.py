"""Swimlane SVG writer (A12 / FR-6). Consumes a lane-grid PositionedDiagram.

Adds swimlane chrome — title bar, per-lane band + header pill, number badges, UML
start/end markers — on top of the shared shape/arrow/font primitives from the graph
writer. Coordinates are absolute (the lane-grid layouter already includes margins), so
unlike the graph writer there is no outer translate. Per-label direction/lang keep the
RTL variant (Phase 4) a geometry-only change.
"""
from __future__ import annotations

from tarseem.model.ir import Marker, PositionedDiagram, PositionedEdge, PositionedNode
from tarseem.render.fonts import FONT_FAMILY, subset_woff2_datauri
from tarseem.render.svg import (
    _arrowhead,
    _esc,
    _label_attrs,
    _num,
    _shape_svg,
)

__all__ = ["render_swimlane_svg"]

_LABEL_W = 160.0  # left header-column width (matches lanegrid geometry)
_TITLE_FILL = "#269973"
_SEPARATOR = "#B0BEC5"
_EDGE_DEFAULT = "#2E8B57"
_MARKER_BLACK = "#000000"


def _collect_chars(diagram: PositionedDiagram) -> frozenset[str]:
    chars: set[str] = set("0123456789.")
    if diagram.title:
        chars.update(diagram.title)
    for band in diagram.lanes:
        chars.update(band.label.text)
    for n in diagram.nodes:
        chars.update(n.label.text)
        if n.badge:
            chars.update(n.badge)
    for e in diagram.edges:
        if e.label:
            chars.update(e.label.text)
    return frozenset(chars)


def _title_bar(diagram: PositionedDiagram, m: float, title_h: float) -> list[str]:
    if not diagram.title:
        return []
    w = diagram.width
    return [
        f'<rect x="{_num(m)}" y="{_num(m)}" width="{_num(w - 2 * m)}" height="{_num(title_h)}" '
        f'rx="6" fill="{_TITLE_FILL}"/>',
        f'<text x="{_num(w / 2)}" y="{_num(m + title_h / 2)}" font-size="18" font-weight="700" '
        f'fill="#FFFFFF" text-anchor="middle" dominant-baseline="central">'
        f"{_esc(diagram.title)}</text>",
    ]


def _lane_band(band, width: float) -> list[str]:
    c = band.hue
    row = c.get("row", "#EEEEEE")
    accent = c.get("label", "#333333")
    chip_h = 56.0
    chip_w = _LABEL_W - 16.0
    chip_x = band.x + 8.0
    chip_y = band.y + (band.height - chip_h) / 2
    return [
        f'<rect x="{_num(band.x)}" y="{_num(band.y)}" width="{_num(band.width)}" '
        f'height="{_num(band.height)}" fill="{row}" stroke="{accent}" stroke-width="1" '
        f'opacity="0.85"/>',
        f'<rect x="{_num(chip_x)}" y="{_num(chip_y)}" width="{_num(chip_w)}" '
        f'height="{_num(chip_h)}" rx="8" fill="{accent}"/>',
        f'<text x="{_num(chip_x + chip_w / 2)}" y="{_num(chip_y + chip_h / 2)}" font-size="13" '
        f'font-weight="700" fill="#FFFFFF" text-anchor="middle" dominant-baseline="central" '
        f"{_label_attrs(band.label)}>{_esc(band.label.text)}</text>",
    ]


def _marker_svg(m: Marker) -> str:
    cx, cy = _num(m.cx), _num(m.cy)
    if m.kind == "start":
        return f'<circle cx="{cx}" cy="{cy}" r="{_num(m.r)}" fill="{_MARKER_BLACK}"/>'
    # end = bullseye: white disc, black ring, black centre
    return (
        f'<circle cx="{cx}" cy="{cy}" r="{_num(m.r)}" fill="#FFFFFF" '
        f'stroke="{_MARKER_BLACK}" stroke-width="2"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{_num(m.r * 0.45)}" fill="{_MARKER_BLACK}"/>'
    )


def _edge_svg(e: PositionedEdge) -> list[str]:
    color = str(e.style.get("stroke", _EDGE_DEFAULT))
    sw = float(e.style.get("width", 2) or 2)
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
            f'<text x="{_num(lx)}" y="{_num(ly)}" font-size="12" fill="{color}" '
            f"{_label_attrs(e.label)}>{_esc(e.label.text)}</text>"
        )
    return out


def _node_svg(n: PositionedNode) -> list[str]:
    out = [_shape_svg(n)]
    accent = str((n.style.get("border") or {}).get("color", "#333333"))
    if n.badge:
        out.append(
            f'<text x="{_num(n.x + 10)}" y="{_num(n.y + 15)}" font-size="12" font-weight="700" '
            f'fill="{accent}" text-anchor="start">{_esc(n.badge)}</text>'
        )
    out.append(
        f'<text x="{_num(n.x + n.width / 2)}" y="{_num(n.y + n.height / 2)}" font-size="12" '
        f'fill="#14281D" {_label_attrs(n.label)}>{_esc(n.label.text)}</text>'
    )
    return out


def render_swimlane_svg(diagram: PositionedDiagram) -> str:
    w, h = diagram.width, diagram.height
    # geometry recovered from the band chrome (layouter owns the absolute coords)
    m = diagram.lanes[0].x if diagram.lanes else 20.0
    title_h = (diagram.lanes[0].y - m) if diagram.lanes else 50.0
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
    parts.extend(_title_bar(diagram, m, title_h))
    for band in diagram.lanes:
        parts.extend(_lane_band(band, w))

    if diagram.lanes:
        sep_x = m + _LABEL_W + 2
        top = diagram.lanes[0].y
        bottom = diagram.lanes[-1].y + diagram.lanes[-1].height
        parts.append(
            f'<line x1="{_num(sep_x)}" y1="{_num(top)}" x2="{_num(sep_x)}" y2="{_num(bottom)}" '
            f'stroke="{_SEPARATOR}" stroke-width="2"/>'
        )

    for e in diagram.edges:  # edges under nodes so arrowheads tuck at borders
        parts.extend(_edge_svg(e))
    for marker in diagram.markers:
        parts.append(_marker_svg(marker))
    for n in diagram.nodes:
        parts.extend(_node_svg(n))

    parts.append("</svg>")
    return "\n".join(parts)
