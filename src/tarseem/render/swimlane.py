"""Swimlane SVG writer (A12 / FR-6). Consumes a lane-grid PositionedDiagram.

Adds swimlane chrome — title bar, per-lane band + header pill, number badges, UML
start/end markers — on top of the shared shape/arrow/font primitives from the graph
writer. Coordinates are absolute (the lane-grid layouter already includes margins), so
unlike the graph writer there is no outer translate. Per-label direction/lang keep the
RTL variant (Phase 4) a geometry-only change.
"""
from __future__ import annotations

from tarseem.geometry import (
    BADGE_R as _BADGE_R,
    CHROME_RADIUS as _CHROME_RADIUS,
    LANE_ACCENT_DEFAULT as _LANE_ACCENT_DEFAULT,
    LANE_ROW_DEFAULT as _LANE_ROW_DEFAULT,
    MARKER_BLACK as _MARKER_BLACK,
    PHASE_FILL as _PHASE_FILL,
    SEPARATOR as _SEPARATOR,
    TITLE_FILL as _TITLE_FILL,
    badge_center,
    chip_rect,
    swimlane_chrome,
    title_bar_box,
)
from tarseem.model.ir import Marker, PositionedDiagram, PositionedEdge, PositionedNode
from tarseem.render.fonts import FONT_FAMILY, subset_woff2_datauri
from tarseem.render.svg import (
    SHADOW_DEF,
    _arrowhead,
    _esc,
    _label_attrs,
    _label_center,
    _num,
    _shape_svg,
    edge_svg_line,
)
from tarseem.render.text import bidi_attrs, resolve_badge_side, resolve_edge_corners

__all__ = ["render_swimlane_svg"]

_EDGE_DEFAULT = "#2E8B57"


def _badge_circle(n: PositionedNode, side: str, accent: str) -> list[str]:
    """Numbered badge as a small filled circle centred on the node's top corner (top-right
    for LTR, top-left for RTL by default; see resolve_badge_side), white number inside."""
    cx, cy = badge_center(n, side)
    num = (n.badge or "").rstrip(".")
    return [
        f'<circle cx="{_num(cx)}" cy="{_num(cy)}" r="{_num(_BADGE_R)}" fill="{accent}" '
        f'stroke="#FFFFFF" stroke-width="1.5"/>',
        f'<text x="{_num(cx)}" y="{_num(cy)}" font-size="11" font-weight="700" fill="#FFFFFF" '
        f'text-anchor="middle" dominant-baseline="central">{_esc(num)}</text>',
    ]


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
        f'height="{_num(band.height)}" rx="{_num(_CHROME_RADIUS)}" '
        f'fill="{_PHASE_FILL}" opacity="0.92"/>',
        f'<text x="{_num(cx)}" y="{_num(band.y + band.height / 2)}" font-size="13" '
        f'font-weight="700" fill="#FFFFFF" {_label_attrs(band.label)}>'
        f"{_esc(band.label.text)}</text>",
    ]


def _lane_band(band, width: float, rtl: bool = False, vertical: bool = False) -> list[str]:
    c = band.hue
    row = c.get("row", _LANE_ROW_DEFAULT)
    accent = c.get("label", _LANE_ACCENT_DEFAULT)
    # header pill: top of the column (vertical) or flow-start side of the row — left for LTR,
    # right for RTL (analysis.md §R-2). Shared geometry so draw.io/pptx place it identically.
    chip_x, chip_y, chip_w, chip_h = chip_rect(band, rtl, vertical)
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
    fill = band.hue.get("label", _PHASE_FILL)  # group bar uses the accent tint
    cx = band.x + band.width / 2
    cy = band.y + band.height / 2
    return [
        f'<rect x="{_num(band.x)}" y="{_num(band.y)}" width="{_num(band.width)}" '
        f'height="{_num(band.height)}" rx="{_num(_CHROME_RADIUS)}" fill="{fill}" opacity="0.92"/>',
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


def _edge_svg(e: PositionedEdge, curved: bool = True) -> list[str]:
    color = str(e.style.get("stroke", _EDGE_DEFAULT))
    sw = float(e.style.get("width", 2) or 2)
    dash = ' stroke-dasharray="6 4"' if e.style.get("style") == "dashed" else ""
    out = [edge_svg_line(list(e.points), color, sw, dash, curved)]
    if len(e.points) >= 2:
        out.append(_arrowhead(e.points[-2], e.points[-1], color))
    if e.label and e.label_xy:
        lx, ly = e.label_xy
        out.append(
            f'<text x="{_num(lx)}" y="{_num(ly)}" font-size="12" fill="{color}" '
            f"{_label_attrs(e.label)}>{_esc(e.label.text)}</text>"
        )
    return out


def _node_svg(n: PositionedNode, rtl: bool = False, badge_side: str = "right") -> list[str]:
    out = [_shape_svg(n)]
    accent = str((n.style.get("border") or {}).get("color", "#333333"))
    if n.badge:
        out.extend(_badge_circle(n, badge_side, accent))
    lcx, lcy = _label_center(n)  # cube/cylinder-aware vertical centring
    out.append(
        f'<text x="{_num(lcx)}" y="{_num(lcy)}" font-size="12" '
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
        title_x, title_top, title_w, title_h = title_bar_box(diagram)
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
        f"<defs>{SHADOW_DEF}</defs>",
        f'<rect width="{_num(w)}" height="{_num(h)}" fill="#FFFFFF"/>',
    ]
    rtl = diagram.direction == "RL"
    vertical = diagram.orientation == "vertical"
    parts.extend(_title_bar(diagram, title_x, title_top, title_w, title_h))
    for group in diagram.lane_groups:  # nested-lane parent gutters (behind the lane bands)
        parts.extend(_lane_group_band(group))
    for band in diagram.lanes:
        parts.extend(_lane_band(band, w, rtl, vertical))

    if diagram.lanes and vertical:
        # actor/label separator runs ACROSS the columns, just below the header pills
        (x1, y1), (x2, y2) = swimlane_chrome(diagram, rtl, vertical).actor_segment
        parts.append(
            f'<line x1="{_num(x1)}" y1="{_num(y1)}" x2="{_num(x2)}" y2="{_num(y2)}" '
            f'stroke="{_SEPARATOR}" stroke-width="2"/>'
        )
    elif diagram.lanes:
        # actor/label separator runs down the header-column side (right under RTL); the phase
        # separators drop through the same lane span [top, bottom].
        chrome = swimlane_chrome(diagram, rtl, vertical)
        sep_x = chrome.actor_p1[0]
        top, bottom = chrome.lane_top, chrome.lane_bottom
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

    badge_side = resolve_badge_side(rtl, diagram.theme)
    edge_curved = resolve_edge_corners(diagram.theme)
    for e in diagram.edges:  # edges under nodes so arrowheads tuck at borders
        parts.extend(_edge_svg(e, edge_curved))
    for marker in diagram.markers:
        parts.append(_marker_svg(marker))
    for n in diagram.nodes:
        parts.extend(_node_svg(n, rtl, badge_side))

    parts.append("</svg>")
    return "\n".join(parts)
