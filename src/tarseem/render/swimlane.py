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
from tarseem.render.text import bidi_attrs

__all__ = ["render_swimlane_svg"]

_LABEL_W = 160.0  # left header-column width (matches lanegrid geometry)
_TITLE_FILL = "#269973"
_SEPARATOR = "#B0BEC5"
_EDGE_DEFAULT = "#2E8B57"
_MARKER_BLACK = "#000000"
_BADGE_INSET_X = 10.0
_BADGE_INSET_Y = 15.0
_CYLINDER_RY = 9.0  # matches the renderer's cylinder cap depth
_PARALLELOGRAM_SLANT = 20.0  # matches the renderer's parallelogram skew


def _badge_baseline(shape: str, y: float) -> float:
    """Badge text baseline. Nudged below curved-top shapes (cylinder) so the number
    clears the top ellipse cap instead of sitting on the curve."""
    if shape == "cylinder":
        return y + _BADGE_INSET_Y + 2 * _CYLINDER_RY
    return y + _BADGE_INSET_Y


def _badge_x(shape: str, x: float) -> float:
    """Badge left edge. Shifted right past the slanted top-left corner of a
    parallelogram so the number sits inside the body, not in the cut-off corner."""
    if shape == "parallelogram":
        return x + _PARALLELOGRAM_SLANT + 4.0
    return x + _BADGE_INSET_X


def _collect_chars(diagram: PositionedDiagram) -> frozenset[str]:
    chars: set[str] = set("0123456789.")
    if diagram.title:
        chars.update(diagram.title)
    for band in diagram.lanes:
        chars.update(band.label.text)
    for group in diagram.lane_groups:  # nested-lane group labels (else they fall back to serif)
        chars.update(group.label.text)
    for n in diagram.nodes:
        chars.update(n.label.text)
        if n.badge:
            chars.update(n.badge)
    for e in diagram.edges:
        if e.label:
            chars.update(e.label.text)
    return frozenset(chars)


def _title_bar(
    diagram: PositionedDiagram, x: float, y: float, width: float, title_h: float
) -> list[str]:
    if not diagram.title:
        return []
    # title bar colour is a theme function (F4): default theme = #269973 (unchanged).
    title = diagram.theme.get("title") or {}
    fill = str(title.get("fill", _TITLE_FILL))
    text_color = str(title.get("text", "#FFFFFF"))
    return [
        f'<rect x="{_num(x)}" y="{_num(y)}" width="{_num(width)}" height="{_num(title_h)}" '
        f'rx="6" fill="{fill}"/>',
        f'<text x="{_num(x + width / 2)}" y="{_num(y + title_h / 2)}" font-size="18" '
        f'font-weight="700" fill="{text_color}" {bidi_attrs(diagram.title)}>'
        f"{_esc(diagram.title)}</text>",
    ]


def _phase_sep_attrs(sep: dict) -> str:
    """Stroke attributes for a phase separator from the resolved `phaseSeparator` options:
    style ("dashed" default | "solid"), color, width."""
    color = str(sep.get("color", _SEPARATOR))
    width = float(sep.get("width", 1.5))
    dash = "" if sep.get("style") == "solid" else ' stroke-dasharray="3 4"'
    return f'stroke="{color}" stroke-width="{_num(width)}"{dash}'


def _phase_band(band, lanes_top: float, lanes_bottom: float, sep: dict) -> list[str]:
    """Phase header pill + a separator at the band's LEFT edge dropping through the lanes
    (FR-6.3). The separator spans only the lane area [lanes_top, lanes_bottom] so it never
    pokes above the swimlane top border or below the bottom. Drawing at the left edge puts a
    separator at the start of the first phase and at every phase boundary (bands tile
    contiguously, so one band's left edge is the previous band's right edge)."""
    cx = band.x + band.width / 2
    return [
        f'<line x1="{_num(band.x)}" y1="{_num(lanes_top)}" x2="{_num(band.x)}" '
        f'y2="{_num(lanes_bottom)}" {_phase_sep_attrs(sep)}/>',
        f'<rect x="{_num(band.x)}" y="{_num(band.y)}" width="{_num(band.width)}" '
        f'height="{_num(band.height)}" rx="5" fill="#37474F" opacity="0.92"/>',
        f'<text x="{_num(cx)}" y="{_num(band.y + band.height / 2)}" font-size="13" '
        f'font-weight="700" fill="#FFFFFF" {_label_attrs(band.label)}>'
        f"{_esc(band.label.text)}</text>",
    ]


def _lane_band(band, width: float, rtl: bool = False, vertical: bool = False) -> list[str]:
    c = band.hue
    row = c.get("row", "#EEEEEE")
    accent = c.get("label", "#333333")
    if vertical:
        # vertical lanes are columns -> header pill sits at the TOP of the column, centered
        # in the header strip (the transposed _LABEL_W band reserved above the first step).
        chip_h = 48.0
        chip_w = band.width - 16.0
        chip_x = band.x + 8.0
        chip_y = band.y + (_LABEL_W - chip_h) / 2
    else:
        chip_h = 56.0
        chip_w = _LABEL_W - 16.0
        # header pill sits on the flow-start side: left for LTR, right for RTL (analysis.md §R-2)
        chip_x = (band.x + band.width - chip_w - 8.0) if rtl else band.x + 8.0
        chip_y = band.y + (band.height - chip_h) / 2
    return [
        f'<rect x="{_num(band.x)}" y="{_num(band.y)}" width="{_num(band.width)}" '
        f'height="{_num(band.height)}" fill="{row}" stroke="{accent}" stroke-width="1" '
        f'opacity="0.85"/>',
        f'<rect x="{_num(chip_x)}" y="{_num(chip_y)}" width="{_num(chip_w)}" '
        f'height="{_num(chip_h)}" rx="8" fill="{accent}"/>',
        f'<text x="{_num(chip_x + chip_w / 2)}" y="{_num(chip_y + chip_h / 2)}" font-size="13" '
        f'font-weight="700" fill="#FFFFFF" {_label_attrs(band.label)}>'
        f"{_esc(band.label.text)}</text>",
    ]


def _lane_group_band(band) -> list[str]:
    """Outer parent-group header for nested lanes (best-effort, AM-6): a narrow coloured
    gutter bar to the left of the child lanes, with the group label rotated to read upward."""
    fill = band.hue.get("label", "#37474F")  # group bar uses the accent tint
    cx = band.x + band.width / 2
    cy = band.y + band.height / 2
    return [
        f'<rect x="{_num(band.x)}" y="{_num(band.y)}" width="{_num(band.width)}" '
        f'height="{_num(band.height)}" rx="6" fill="{fill}" opacity="0.92"/>',
        f'<text x="{_num(cx)}" y="{_num(cy)}" font-size="12" font-weight="700" fill="#FFFFFF" '
        f'transform="rotate(-90 {_num(cx)} {_num(cy)})" {_label_attrs(band.label)}>'
        f"{_esc(band.label.text)}</text>",
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


def _node_svg(n: PositionedNode, rtl: bool = False) -> list[str]:
    out = [_shape_svg(n)]
    accent = str((n.style.get("border") or {}).get("color", "#333333"))
    if n.badge:
        by = _badge_baseline(n.shape, n.y)
        # badge corner mirrors under RTL: top-right (anchor end) instead of top-left
        if rtl:
            bx = n.x + n.width - _BADGE_INSET_X
            anchor = "end"
        else:
            bx = _badge_x(n.shape, n.x)
            anchor = "start"
        out.append(
            f'<text x="{_num(bx)}" y="{_num(by)}" font-size="12" font-weight="700" '
            f'fill="{accent}" text-anchor="{anchor}">{_esc(n.badge)}</text>'
        )
    out.append(
        f'<text x="{_num(n.x + n.width / 2)}" y="{_num(n.y + n.height / 2)}" font-size="12" '
        f'fill="#14281D" {_label_attrs(n.label)}>{_esc(n.label.text)}</text>'
    )
    return out


def render_swimlane_svg(diagram: PositionedDiagram) -> str:
    w, h = diagram.width, diagram.height
    # Title geometry recovered from band chrome (layouter owns absolute coords). The top margin
    # is the canvas inset (height - last lane bottom), independent of the LEFT inset — which a
    # nested-lane group gutter shifts. The bar spans the full chrome width (group gutter through
    # the last lane's right edge) so it always reaches the swimlane's end border. It stops at
    # the phase header when phases exist, else at the first lane, so the titles never overlap.
    if diagram.lanes:
        title_x = min([b.x for b in diagram.lanes] + [g.x for g in diagram.lane_groups])
        title_right = max(b.x + b.width for b in diagram.lanes)
        title_w = title_right - title_x
        title_top = h - (diagram.lanes[-1].y + diagram.lanes[-1].height)
        title_bottom = diagram.phases[0].y if diagram.phases else diagram.lanes[0].y
        title_h = title_bottom - title_top
    else:
        title_x, title_top, title_w, title_h = 20.0, 20.0, w - 40.0, 50.0
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
    m = diagram.lanes[0].x if diagram.lanes else 20.0  # lane-left, for the actor separator
    rtl = diagram.direction == "RL"
    vertical = diagram.orientation == "vertical"
    parts.extend(_title_bar(diagram, title_x, title_top, title_w, title_h))
    for group in diagram.lane_groups:  # nested-lane parent gutters (behind the lane bands)
        parts.extend(_lane_group_band(group))
    for band in diagram.lanes:
        parts.extend(_lane_band(band, w, rtl, vertical))

    if diagram.lanes and vertical:
        # actor/label separator runs ACROSS the columns, just below the header pills
        sep_y = diagram.lanes[0].y + _LABEL_W
        left = diagram.lanes[0].x
        right = diagram.lanes[-1].x + diagram.lanes[-1].width
        parts.append(
            f'<line x1="{_num(left)}" y1="{_num(sep_y)}" x2="{_num(right)}" y2="{_num(sep_y)}" '
            f'stroke="{_SEPARATOR}" stroke-width="2"/>'
        )
    elif diagram.lanes:
        # actor/label separator runs down the header-column side (right under RTL)
        sep_x = (w - m - _LABEL_W) if rtl else m + _LABEL_W
        top = diagram.lanes[0].y
        bottom = diagram.lanes[-1].y + diagram.lanes[-1].height
        parts.append(
            f'<line x1="{_num(sep_x)}" y1="{_num(top)}" x2="{_num(sep_x)}" y2="{_num(bottom)}" '
            f'stroke="{_SEPARATOR}" stroke-width="2"/>'
        )
        sep = diagram.phase_separator
        for phase in diagram.phases:  # phase header bands + left-edge separators (FR-6.3)
            parts.extend(_phase_band(phase, top, bottom, sep))
        if diagram.phases:  # closing separator at the right edge of the last phase
            last = max(diagram.phases, key=lambda p: p.x + p.width)
            edge = last.x + last.width
            parts.append(
                f'<line x1="{_num(edge)}" y1="{_num(top)}" x2="{_num(edge)}" '
                f'y2="{_num(bottom)}" {_phase_sep_attrs(sep)}/>'
            )

    for e in diagram.edges:  # edges under nodes so arrowheads tuck at borders
        parts.extend(_edge_svg(e))
    for marker in diagram.markers:
        parts.append(_marker_svg(marker))
    for n in diagram.nodes:
        parts.extend(_node_svg(n, rtl))

    parts.append("</svg>")
    return "\n".join(parts)
