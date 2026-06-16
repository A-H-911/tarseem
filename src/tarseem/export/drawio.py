"""draw.io (.drawio / mxGraph XML) writer — the first-class editable export (08 §3, D2:C).

Consumes the positioned IR (ADR-001: writers never lay out) and emits native draw.io cells:
a ``swimlane`` pool with child ``swimlane`` lanes, shape cells parented into the lane that
geometrically contains them (so dragging a lane moves its nodes, as diagrams.net users
expect), and edges whose exact route travels as ``sourcePoint``/``targetPoint`` + an
``mxPoint`` waypoint array under ``edgeStyle=none`` (so draw.io draws the IR polyline verbatim
rather than re-routing it). Edges are floating, not node-bound: the IR carries no edge→node
identity, and exact geometry is the contract.

Constraints honoured:
- **Verified style-key subset only** (R-14): every style token below is a documented mxGraph
  key (``rounded``, ``rhombus``, ``shape=cylinder3``…). No undocumented/guessed keys.
- **Uncompressed XML** (08 §3): the ``<mxGraphModel>`` is inlined as plain XML, never the
  base64+deflate payload draw.io also accepts — portable + diffable.
- **Deterministic** (invariant 7): cell ids derive from node/edge ids; provenance carries no
  wall-clock. Same diagram ⇒ byte-identical file.
- **RTL**: labels that resolve to RTL get ``writingDirection=rtl`` on their cell.

Fidelity is reported, never silently dropped (invariant 6): see ``_report``.
"""
from __future__ import annotations

import re
from pathlib import Path

from lxml import etree

from tarseem.export.result import WriteResult
from tarseem.geometry import (
    BADGE_R as _BADGE_R,
    CHROME_RADIUS as _CHROME_RADIUS,
    DEFAULT_FILL as _DEFAULT_FILL,
    DEFAULT_STROKE as _DEFAULT_STROKE,
    DEFAULT_TEXT as _DEFAULT_TEXT,
    EDGE_WIDTH_DEFAULT as _EDGE_WIDTH_DEFAULT,
    ER_BORDER as _ER_BORDER,
    ER_KEY_FILL as _ER_KEY_FILL,
    ER_PAD_X as _ER_PAD_X,
    ER_ROW_SEP as _ER_ROW_SEP,
    ER_TITLE_FILL as _ER_TITLE_FILL,
    LANE_ACCENT_DEFAULT as _LANE_ACCENT_DEFAULT,
    LANE_ROW_DEFAULT as _LANE_ROW_DEFAULT,
    MARKER_BLACK as _MARKER_BLACK,
    PHASE_FILL as _PHASE_FILL,
    SEPARATOR as _SEPARATOR,
    SEQ_ACT_BORDER as _SEQ_ACT_BORDER,
    SEQ_MARGIN as _SEQ_MARGIN,
    SEQ_STEM as _SEQ_STEM,
    TITLE_FILL as _TITLE_FILL,
    chip_rect,
    swimlane_chrome,
    title_bar_box,
)
from tarseem.model.ir import Label, Marker, PositionedDiagram, PositionedNode
from tarseem.render.text import (
    has_rtl,
    resolve_badge_side,
    resolve_direction,
    resolve_edge_corners,
    resolve_entity_corners,
)
from tarseem.report import CapabilityWarning, build_capability_report

__all__ = ["write_drawio", "to_drawio_xml"]

# Verified mxGraph style prefixes per IR shape. Documented keys only (R-14).
_SHAPE_STYLE: dict[str, str] = {
    "rect": "",
    "roundrect": "rounded=1;",
    "rounded": "rounded=1;",
    "stadium": "rounded=1;arcSize=50;",
    # mxGraph names the diamond via shape=rhombus (NOT a boolean `rhombus=1`, which parses as a
    # stray property and silently falls back to a rectangle — caught by the draw.io round-trip).
    "diamond": "shape=rhombus;perimeter=rhombusPerimeter;",
    "parallelogram": "shape=parallelogram;perimeter=parallelogramPerimeter;",
    # size=9 MUST match render/svg.py cylinder ry (shallow cap = engine's tall-can look; the
    # cylinder3 default cap is deeper and reads as a shorter cylinder).
    "cylinder": "shape=cylinder3;size=9;shadow=1;",
    "document": "shape=document;",
    # cube depth = 14 (MUST match render/svg.py + measure._CUBE_DEPTH). draw.io's cube extrudes
    # depth at top+LEFT (front face bottom-right) — the MIRROR of the engine (top+right); flipH=1
    # mirrors it back so the 3D faces and the bottom-left front face match the SVG. draw.io centres
    # its own cube label on the bbox + ignores depth, so the label is a SEPARATE front-face text
    # cell (see _emit_cube_label) which flipH leaves untouched.
    "cube": "shape=cube;size=14;flipH=1;shadow=1;",
    "table": "",  # ER entity → plain box; attribute rows folded into label (reported partial)
}

# Name the SVG's underlying font family so draw.io references the same face, with a sans-serif
# fallback. draw.io can't embed fonts (fonts ceiling): exact glyphs match only where Cairo is
# installed (e.g. draw.io Desktop); elsewhere the fallback keeps text SANS (matching Cairo's
# style), never the browser's serif default that a bare `fontFamily=Cairo` would trigger.
_FONT = "fontFamily=Cairo,sans-serif;"

# Lane/ER/sequence chrome constants are shared with the SVG renderers via tarseem.geometry
# (ADR-007: draw.io reproduces render/swimlane.py + render/er.py geometry exactly). One source
# of truth — no per-writer copies to keep in lockstep.
_CUBE_DEPTH = 14.0  # MUST match render/svg.py + measure._CUBE_DEPTH (shape geometry, per-writer)


def _cell_id(prefix: str, raw: str) -> str:
    """Stable, draw.io-safe id derived from an IR id (never a random GUID)."""
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", raw)
    return f"{prefix}_{safe}"


def _rtl(label: Label | None) -> bool:
    if label is None:
        return False
    return resolve_direction(label.direction, label.text) == "rtl" or has_rtl(label.text)


def _style(tokens: str, label: Label | None, *, rtl_ok: bool = True) -> str:
    # RTL controls bidi base direction only (writingDirection); block alignment stays the
    # draw.io vertex default (centered), matching the SVG (text-anchor=middle). Forcing
    # align=right here was the "RTL text not horizontally centered" bug.
    style = tokens + _FONT
    if rtl_ok and _rtl(label):
        style += "writingDirection=rtl;"
    return style


def _fill(style: dict) -> str:
    return str(style.get("fill", _DEFAULT_FILL))


def _stroke(style: dict) -> str:
    border = style.get("border") or {}
    return str(border.get("color", _DEFAULT_STROKE))


def _stroke_w(style: dict) -> float:
    """Border width — same source + default (1) as the SVG ``_node_stroke``, so a spec's
    ``border.width`` controls both writers."""
    border = style.get("border") or {}
    return float(border.get("width", 1) or 1)


def _font_color(style: dict) -> str | None:
    text = style.get("text") or {}
    color = text.get("color")
    return str(color) if color else None


def _node_style(node: PositionedNode) -> str:
    base = _SHAPE_STYLE.get(node.shape, "")
    tokens = f"{base}html=1;whiteSpace=wrap;fillColor={_fill(node.style)};"
    if node.shape == "cylinder":  # drop text onto the body, below the top cap (≈ svg _CYL_CAP*2)
        tokens += "verticalAlign=middle;spacingTop=12;"
    tokens += f"strokeColor={_stroke(node.style)};strokeWidth={_fmt(_stroke_w(node.style))};"
    # default to the engine's label colour (#14281D) when the spec sets none — mxGraph would
    # otherwise fall back to black, diverging from the SVG (cube label already defaults the same).
    tokens += f"fontColor={_font_color(node.style) or _DEFAULT_TEXT};"
    return _style(tokens, node.label)


def _add_geometry(cell: etree._Element, x: float, y: float, w: float, h: float) -> None:
    geo = etree.SubElement(cell, "mxGeometry")
    geo.set("x", _fmt(x))
    geo.set("y", _fmt(y))
    geo.set("width", _fmt(w))
    geo.set("height", _fmt(h))
    geo.set("as", "geometry")


def _fmt(v: float) -> str:
    return f"{v:.2f}".rstrip("0").rstrip(".")


def _label_text(node: PositionedNode) -> str:
    """Node value. Two foldings (no native draw.io cell for either; reported in _report):
    - auto-number badge → label prefix;
    - ER attribute rows → ``<br>``-separated lines under the entity name (html=1 renders them).
    """
    return node.label.text


def _all_chars(diagram: PositionedDiagram) -> frozenset[str]:
    """Every glyph the diagram renders — for the embedded-font subset."""
    chars: set[str] = set("0123456789.PKF")  # badge digits + ER key tags
    if diagram.title:
        chars.update(diagram.title)
    for n in diagram.nodes:
        chars.update(n.label.text)
        if n.badge:
            chars.update(n.badge)
        for r in n.rows:
            chars.update(r.label.text)
    for e in diagram.edges:
        if e.label:
            chars.update(e.label.text)
    for band in diagram.lanes:
        chars.update(band.label.text)
    for group in diagram.lane_groups:
        chars.update(group.label.text)
    for phase in diagram.phases:
        chars.update(phase.label.text)
    return frozenset(chars)


def _embed_font(root: etree._Element, diagram: PositionedDiagram) -> None:
    """Embed the bundled Cairo subset INTO the file so the .drawio renders in Cairo with zero
    setup (raises the fonts ceiling). mxGraph turns a cell's ``fontSource`` (a URL-encoded font
    URL — a self-contained data: URI here) into a global ``@font-face`` for ``fontFamily``, so a
    single registering cell makes every ``fontFamily=Cairo`` cell use it — no per-cell bloat.
    Deterministic: the subset is timestamp-free + codepoint-sorted, the registering cell is the
    first text cell in document order."""
    import urllib.parse

    from tarseem.render.fonts import subset_woff2_datauri

    chars = _all_chars(diagram)
    if not chars:
        return
    src = urllib.parse.quote(f"data:font/woff2;base64,{subset_woff2_datauri(chars)}", safe="")
    # pure family name (no fallback) so the @font-face registers for "Cairo"; other cells keep
    # "Cairo,sans-serif" and resolve to this now-defined face.
    register = f"fontFamily=Cairo;fontSource={src};"
    for cell in root.iter("mxCell"):
        style = cell.get("style") or ""
        if cell.get("value") and _FONT in style:
            cell.set("style", style.replace(_FONT, register, 1))
            return


def to_drawio_xml(diagram: PositionedDiagram, meta: dict[str, str] | None = None) -> str:
    """Serialize ``diagram`` to an uncompressed .drawio XML string (provenance-commented)."""
    mxfile = etree.Element("mxfile", host="tarseem", type="device")
    diagram_el = etree.SubElement(mxfile, "diagram", id="tarseem-diagram", name="Tarseem")
    model = etree.SubElement(
        diagram_el,
        "mxGraphModel",
        dx=_fmt(diagram.width),
        dy=_fmt(diagram.height),
        grid="0",
        guides="1",
        connect="1",
        arrows="1",
        page="1",
        pageWidth=_fmt(diagram.width),
        pageHeight=_fmt(diagram.height),
    )
    root = etree.SubElement(model, "root")
    etree.SubElement(root, "mxCell", id="0")
    etree.SubElement(root, "mxCell", id="1", parent="0")

    # Chrome (lane bands/headers/phases, or sequence lifelines+activations) drawn first so
    # nodes/edges sit on top. ADR-007: explicit rects, not native swimlane cells.
    if diagram.lanes:
        _emit_swimlane_chrome(root, diagram)
    elif diagram.diagram_type == "sequence":
        _emit_sequence_chrome(root, diagram)

    rtl = diagram.direction == "RL"
    badge_side = resolve_badge_side(rtl, diagram.theme)
    entity_round = resolve_entity_corners(diagram.theme) == "rounded"
    for node in diagram.nodes:
        if node.rows:  # ER entity → explicit table cells matching render/er.py (bug #2)
            _emit_entity(root, node, rtl, entity_round)
            continue
        if node.shape in ("initial", "final"):  # state pseudostates → ellipses, not a plain box
            _emit_pseudostate(root, node)
            continue
        is_cube = node.shape == "cube"
        cell = etree.SubElement(
            root,
            "mxCell",
            id=_cell_id("n", node.id),
            value="" if is_cube else _label_text(node),  # cube label is a separate front-face cell
            style=_node_style(node),
            vertex="1",
            parent="1",
        )
        _add_geometry(cell, node.x, node.y, node.width, node.height)
        if is_cube:
            _emit_cube_label(root, node)
        if node.badge:  # numbered badge as a corner circle, not folded into the label (bug #3/#4)
            _emit_badge(root, node, badge_side)

    for marker in diagram.markers:
        _emit_marker(root, marker)

    curved = resolve_edge_corners(diagram.theme)
    edge_w = _EDGE_WIDTH_DEFAULT.get(diagram.diagram_type, 1.0)
    for i, edge in enumerate(diagram.edges):
        _emit_edge(root, edge, i, curved, edge_w)

    _embed_font(root, diagram)  # self-contained Cairo subset → renders in Cairo with zero setup
    xml = etree.tostring(mxfile, pretty_print=True, encoding="unicode")
    if meta:
        from tarseem.export.metadata import as_comment

        xml = f"{as_comment(meta)}\n{xml}"
    return xml


def _rect_cell(
    root: etree._Element, cell_id: str, rect: tuple[float, float, float, float], style: str,
    value: str = "",
) -> None:
    cell = etree.SubElement(
        root, "mxCell", id=cell_id, value=value, style=style, vertex="1", parent="1"
    )
    _add_geometry(cell, *rect)


def _line_cell(
    root: etree._Element, cell_id: str, p1: tuple[float, float], p2: tuple[float, float],
    color: str, width: float, dashed: bool = False,
) -> None:
    dash = "dashed=1;" if dashed else ""
    cell = etree.SubElement(
        root,
        "mxCell",
        id=cell_id,
        style=f"endArrow=none;startArrow=none;html=1;strokeColor={color};strokeWidth={_fmt(width)};{dash}",
        edge="1",
        parent="1",
    )
    geo = etree.SubElement(cell, "mxGeometry", relative="1")
    geo.set("as", "geometry")
    _point(geo, p1, "sourcePoint")
    _point(geo, p2, "targetPoint")


def _emit_swimlane_chrome(root: etree._Element, diagram: PositionedDiagram) -> None:
    """Draw swimlane chrome as explicit cells matching render/swimlane.py exactly (ADR-007):
    title bar, per-lane band + header chip (left for LTR, right for RTL), phase bands +
    separators, the actor separator, and nested-lane group gutters. NOT native swimlanes."""
    lanes = diagram.lanes
    rtl = diagram.direction == "RL"
    vertical = diagram.orientation == "vertical"

    _emit_title_bar(root, diagram)

    for group in diagram.lane_groups:  # nested-lane parent gutters, behind the bands
        fill = (group.hue or {}).get("label", _PHASE_FILL)
        _rect_cell(
            root,
            _cell_id("lanegroup", group.id),
            (group.x, group.y, group.width, group.height),
            f"rounded=1;absoluteArcSize=1;arcSize={_fmt(_CHROME_RADIUS)};html=1;fillColor={fill};"
            f"strokeColor=none;fontColor=#FFFFFF;fontStyle=1;opacity=92;horizontal=0;{_FONT}",
            group.label.text,
        )

    for band in lanes:
        hue = band.hue or {}
        row = hue.get("row", _LANE_ROW_DEFAULT)
        accent = hue.get("label", _LANE_ACCENT_DEFAULT)
        _rect_cell(
            root,
            _cell_id("lane", band.id),
            (band.x, band.y, band.width, band.height),
            f"rounded=0;html=1;fillColor={row};strokeColor={accent};opacity=85;",
        )
        chip = chip_rect(band, rtl, vertical)
        # strokeColor=none: the SVG lane chip is fill-only; without this mxGraph draws a default
        # black 1px border (the "actor/user shapes have black borders" divergence).
        chip_style = _style(
            f"rounded=1;arcSize=14;html=1;fillColor={accent};strokeColor=none;fontColor=#FFFFFF;"
            "fontStyle=1;fontSize=13;",
            band.label,
        )
        _rect_cell(root, _cell_id("lanechip", band.id), chip, chip_style, band.label.text)

    _emit_separators(root, diagram, rtl, vertical)


def _emit_title_bar(root: etree._Element, diagram: PositionedDiagram) -> None:
    """Title bar — geometry from the shared tarseem.geometry.title_bar_box."""
    if not diagram.title or not diagram.lanes:
        return
    title = diagram.theme.get("title") or {}
    fill = str(title.get("fill", _TITLE_FILL))
    text_color = str(title.get("text", "#FFFFFF"))
    _rect_cell(
        root,
        "title",
        title_bar_box(diagram),
        _style(
            f"rounded=1;arcSize=6;html=1;fillColor={fill};strokeColor=none;fontColor={text_color};"
            "fontStyle=1;fontSize=18;",
            None,
        ),
        diagram.title,
    )


def _emit_separators(
    root: etree._Element, diagram: PositionedDiagram, rtl: bool, vertical: bool
) -> None:
    """Actor separator + phase bands/separators — geometry from tarseem.geometry.swimlane_chrome."""
    chrome = swimlane_chrome(diagram, rtl, vertical)
    if vertical:
        _line_cell(root, "actorsep", *chrome.actor_segment, _SEPARATOR, 2.0)
        return
    top, bottom = chrome.lane_top, chrome.lane_bottom
    _line_cell(root, "actorsep", *chrome.actor_segment, _SEPARATOR, 2.0)
    sep = diagram.phase_separator or {}
    color = str(sep.get("color", _SEPARATOR))
    width = float(sep.get("width", 1.5))
    dashed = sep.get("style") != "solid"
    for phase in diagram.phases:
        _line_cell(root, _cell_id("phasesep", phase.id), (phase.x, top), (phase.x, bottom),
                   color, width, dashed)
        _rect_cell(
            root,
            _cell_id("phase", phase.id),
            (phase.x, phase.y, phase.width, phase.height),
            _style(
                f"rounded=1;absoluteArcSize=1;arcSize={_fmt(_CHROME_RADIUS)};html=1;"
                f"fillColor={_PHASE_FILL};strokeColor=none;fontColor=#FFFFFF;fontStyle=1;"
                "fontSize=13;opacity=92;",
                phase.label,
            ),
            phase.label.text,
        )
    if diagram.phases:
        last = max(diagram.phases, key=lambda p: p.x + p.width)
        edge = last.x + last.width
        _line_cell(root, "phasesep_end", (edge, top), (edge, bottom), color, width, dashed)


def _emit_sequence_chrome(root: etree._Element, diagram: PositionedDiagram) -> None:
    """Sequence lifelines + activation bars matching render/sequence.py (note #4): a dashed
    stem descends from each participant head; activation bars are white rects on the stems.
    Also the centered diagram title — the engine renders titles for sequence (and swimlane);
    only swimlane had one in draw.io before, so non-lane sequence titles were dropped."""
    if diagram.title:  # centered title in the top margin band — MUST match render/sequence.py
        _rect_cell(
            root,
            "title",
            (0.0, 0.0, diagram.width, _SEQ_MARGIN),
            _style(
                "text;html=1;align=center;verticalAlign=middle;fontSize=18;fontStyle=1;"
                f"fontColor={_DEFAULT_TEXT};",
                Label(text=diagram.title),
            ),
            diagram.title,
        )
    bottom_y = diagram.height - _SEQ_MARGIN
    for node in diagram.nodes:
        cx = node.x + node.width / 2
        _line_cell(
            root, _cell_id("stem", node.id),
            (cx, node.y + node.height), (cx, bottom_y), _SEQ_STEM, 1.5, dashed=True,
        )
    for i, act in enumerate(diagram.activations):
        _rect_cell(
            root, f"activation_{i}",
            (act.x, act.y, act.width, act.height),
            f"rounded=0;html=1;fillColor=#FFFFFF;strokeColor={_SEQ_ACT_BORDER};strokeWidth=1.5;",
        )


def _emit_marker(root: etree._Element, marker: Marker) -> None:
    """UML start/end markers matching render/swimlane.py _marker_svg (bug #4): start = solid
    black dot; end = bullseye (white disc, black ring, solid black centre)."""
    mid = f"{marker.kind}_{_fmt(marker.cx)}_{_fmt(marker.cy)}"
    r = marker.r
    if marker.kind == "start":
        _rect_cell(
            root, _cell_id("marker", mid),
            (marker.cx - r, marker.cy - r, 2 * r, 2 * r),
            f"ellipse;html=1;fillColor={_MARKER_BLACK};strokeColor={_MARKER_BLACK};",
        )
        return
    # end: outer white disc with black ring, then a solid black inner dot (r * 0.45)
    _rect_cell(
        root, _cell_id("marker", mid),
        (marker.cx - r, marker.cy - r, 2 * r, 2 * r),
        f"ellipse;html=1;fillColor=#FFFFFF;strokeColor={_MARKER_BLACK};strokeWidth=2;",
    )
    ir = r * 0.45
    _rect_cell(
        root, _cell_id("markerdot", mid),
        (marker.cx - ir, marker.cy - ir, 2 * ir, 2 * ir),
        f"ellipse;html=1;fillColor={_MARKER_BLACK};strokeColor=none;",
    )


def _emit_pseudostate(root: etree._Element, node: PositionedNode) -> None:
    """State-machine initial/final pseudostates as ellipses matching render/svg.py (they have no
    entry in _SHAPE_STYLE, so they'd otherwise fall back to a plain white box). initial = a solid
    dot filled with the stroke colour; final = a bullseye (outer ring + inner solid dot)."""
    stroke = _stroke(node.style)
    r = min(node.width, node.height) / 2
    cx, cy = node.x + node.width / 2, node.y + node.height / 2
    if node.shape == "initial":
        _rect_cell(
            root, _cell_id("state", node.id), (cx - r, cy - r, 2 * r, 2 * r),
            f"ellipse;html=1;fillColor={stroke};strokeColor=none;",
        )
        return
    sw = _stroke_w(node.style)
    _rect_cell(
        root, _cell_id("state", node.id), (cx - r, cy - r, 2 * r, 2 * r),
        f"ellipse;html=1;fillColor={_fill(node.style)};strokeColor={stroke};"
        f"strokeWidth={_fmt(sw)};",
    )
    ir = r * 0.5  # inner dot radius — MUST match render/svg.py final pseudostate
    _rect_cell(
        root, _cell_id("statedot", node.id), (cx - ir, cy - ir, 2 * ir, 2 * ir),
        f"ellipse;html=1;fillColor={stroke};strokeColor=none;",
    )


def _emit_badge(root: etree._Element, node: PositionedNode, side: str) -> None:
    """Numbered badge as a small corner circle holding the number — corner ``side`` resolved
    by resolve_badge_side (default LTR -> right, RTL -> left; theme.badgeCorner overrides)."""
    num = (node.badge or "").rstrip(".")
    accent = str((node.style.get("border") or {}).get("color", _LANE_ACCENT_DEFAULT))
    cx = node.x + node.width if side == "right" else node.x
    _rect_cell(
        root,
        _cell_id("badge", node.id),
        (cx - _BADGE_R, node.y - _BADGE_R, 2 * _BADGE_R, 2 * _BADGE_R),
        f"ellipse;html=1;fillColor={accent};strokeColor=#FFFFFF;fontColor=#FFFFFF;"
        f"fontStyle=1;fontSize=11;{_FONT}",
        num,
    )


def _emit_cube_label(root: etree._Element, node: PositionedNode) -> None:
    """Cube label as a separate text cell centred over the FRONT face (draw.io centres its own
    cube label on the bbox and ignores the depth faces) — matches the engine `_label_center`."""
    d = _CUBE_DEPTH
    fc = _font_color(node.style) or "#14281D"
    style = _style(f"text;html=1;align=center;verticalAlign=middle;fontColor={fc};", node.label)
    _rect_cell(
        root,
        _cell_id("cubelabel", node.id),
        (node.x, node.y + d, node.width - d, node.height - d),
        style,
        node.label.text,
    )


def _emit_entity(
    root: etree._Element, node: PositionedNode, rtl: bool, rounded: bool = True
) -> None:
    """ER entity as an explicit table matching render/er.py / out/er-shop.png: rounded (default)
    container + dark title bar, per-row separators + attribute text, gold/blue PK/FK pills.
    ``rounded`` follows theme.entityCorners. The title shares the container's corner radius so the
    header top aligns with the rounded outline (no poke-out); its bottom rounds slightly inward —
    the closest draw.io's simple styles get to the SVG's rounded-top/square-bottom header."""
    x, y, w, h = node.x, node.y, node.width, node.height
    title_h = node.rows[0].y_offset if node.rows else h
    corner = "rounded=1;absoluteArcSize=1;arcSize=6;" if rounded else "rounded=0;"
    _rect_cell(
        root,
        _cell_id("er", node.id),
        (x, y, w, h),
        f"{corner}html=1;fillColor=#FFFFFF;strokeColor={_ER_BORDER};strokeWidth=1.5;",
    )
    _rect_cell(
        root,
        _cell_id("ertitle", node.id),
        (x, y, w, title_h),
        _style(
            f"{corner}html=1;fillColor={_ER_TITLE_FILL};strokeColor=none;fontColor=#FFFFFF;"
            "fontStyle=1;fontSize=13;",
            node.label,
        ),
        node.label.text,
    )
    for r in node.rows:
        ry = y + r.y_offset
        rid = f"{node.id}_{r.id}"
        _line_cell(root, _cell_id("errow", rid), (x, ry), (x + w, ry), _ER_ROW_SEP, 1.0)
        align = "right" if _rtl(r.label) else "left"
        wd = "writingDirection=rtl;" if _rtl(r.label) else ""
        _rect_cell(
            root,
            _cell_id("erattr", rid),
            (x + _ER_PAD_X, ry, w - 2 * _ER_PAD_X, r.height),
            f"text;html=1;align={align};verticalAlign=middle;fontColor={_DEFAULT_TEXT};"
            f"fontSize=12;{wd}{_FONT}",
            r.label.text,
        )
        if r.key:
            tw = 22.0
            ky = ry + r.height / 2
            fill = _ER_KEY_FILL.get(r.key, "#777777")
            _rect_cell(
                root,
                _cell_id("erkey", rid),
                (x + w - _ER_PAD_X - tw, ky - 8, tw, 16),
                # absolute 3px radius MUST match render/er.py _key_tag rx=3 (was a 30% pill);
                # strokeColor=none matches the fill-only SVG pill (no default black border).
                f"rounded=1;absoluteArcSize=1;arcSize=3;html=1;fillColor={fill};strokeColor=none;"
                f"fontColor=#FFFFFF;fontStyle=1;fontSize=10;{_FONT}",
                r.key,
            )


def _emit_edge(
    root: etree._Element, edge, index: int, curved: bool = True, width: float = 1.0,
) -> None:
    from tarseem.model.ir import PositionedEdge

    assert isinstance(edge, PositionedEdge)
    dashed = edge.style.get("style") == "dashed"
    stroke = str(edge.style.get("stroke", _DEFAULT_STROKE))
    sw = float(edge.style.get("width", width) or width)  # spec width overrides family default
    # edgeStyle=none + explicit endpoints/waypoints => draw.io draws EXACTLY the IR polyline.
    # We deliberately do NOT bind source/target cells: the IR has no edge→node identity, and a
    # bound orthogonal edge would let draw.io re-route and discard our exact mxPoints. Floating
    # edges trade live node-reconnection for guaranteed geometry — the route is the contract.
    # rounded=1 (curved corners) is the default, matching the engine SVG (theme.edgeCorners).
    rounded = "1" if curved else "0"
    style = f"edgeStyle=none;rounded={rounded};html=1;strokeColor={stroke};strokeWidth={_fmt(sw)};"
    if dashed:
        style += "dashed=1;"
    cell = etree.SubElement(
        root, "mxCell", id=_cell_id("e", edge.id or f"edge{index}"), value="", style=style,
        edge="1", parent="1",
    )
    geo = etree.SubElement(cell, "mxGeometry", relative="1")
    geo.set("as", "geometry")
    pts = edge.points
    if pts:
        _point(geo, pts[0], "sourcePoint")
        _point(geo, pts[-1], "targetPoint")
    interior = pts[1:-1] if len(pts) > 2 else ()
    if interior:
        arr = etree.SubElement(geo, "Array", {"as": "points"})
        for px, py in interior:
            etree.SubElement(arr, "mxPoint", x=_fmt(px), y=_fmt(py))
    # Label as a SEPARATE text cell at the (already off-line) label_xy — draw.io would otherwise
    # centre an edge value ON the line, ignoring our offset. Matches the SVG/PPTX placement.
    if edge.label is not None and edge.label_xy is not None:
        lx, ly = edge.label_xy
        lw = max(40.0, len(edge.label.text) * 7.0)
        _rect_cell(
            root,
            _cell_id("elabel", edge.id or f"edge{index}"),
            (lx - lw / 2, ly - 8.0, lw, 16.0),
            _style(
                f"text;html=1;align=center;verticalAlign=middle;fontColor={stroke};", edge.label
            ),
            edge.label.text,
        )


def _point(geo: etree._Element, xy: tuple[float, float], role: str) -> None:
    etree.SubElement(geo, "mxPoint", x=_fmt(xy[0]), y=_fmt(xy[1]), **{"as": role})


def write_drawio(
    diagram: PositionedDiagram, out_path: str | Path, meta: dict[str, str] | None = None
) -> WriteResult:
    """Write ``diagram`` to ``out_path`` as uncompressed .drawio XML. Returns the path + a
    CapabilityReport declaring the writer's fidelity ceiling for this diagram."""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(to_drawio_xml(diagram, meta), encoding="utf-8")
    return WriteResult(path=out, report=_report(diagram))


def _report(diagram: PositionedDiagram):
    warnings: list[CapabilityWarning] = []
    supports = {
        "shapes": "full",
        # ADR-007: lanes drawn as explicit rects + header chips matching the SVG (incl. RTL
        # right-side flip + phase bands), NOT native draw.io swimlanes — so visually full,
        # but the lanes are static (not draggable containers); flagged below.
        "lanes": "full" if diagram.lanes else "none",
        "phases": "full" if diagram.phases else "none",
        "badges": "full",
        "markers": "full",
        "edge_routes": "full",
        "edge_labels": "full",
        "curved_edges": "none",
        "ports": "partial" if any(n.rows for n in diagram.nodes) else "none",
        "gradients": "none",
        # The bundled Cairo subset is embedded INTO the file (``_embed_font``), so it renders in
        # Cairo with zero setup — ``full`` under the shared definition (renders with no external
        # font installed). Was stale ``none`` before the round-7 embed (report.faithful_*).
        "fonts_embedded": "full",
        "rtl_shaping": "partial",
        "theme_fidelity": "partial",
        "metadata": "full",
    }
    unknown_shapes = sorted(
        {n.shape for n in diagram.nodes if n.shape not in _SHAPE_STYLE}
    )
    for shape in unknown_shapes:
        supports["shapes"] = "partial"
        warnings.append(
            CapabilityWarning(
                "feature-approximated", "shapes", f"shape {shape!r} drawn as a plain box"
            )
        )
    if diagram.lanes:
        warnings.append(
            CapabilityWarning(
                "editability-limited",
                "lanes",
                "lanes are static rects matching the SVG, not draggable swimlanes (ADR-007)",
            )
        )
    if any(n.rows for n in diagram.nodes):
        warnings.append(
            CapabilityWarning(
                "feature-approximated",
                "ports",
                "ER edges anchored to rows via the exact route; not logical draw.io table ports",
            )
        )
    if any(_rtl(n.label) for n in diagram.nodes):
        warnings.append(
            CapabilityWarning(
                "feature-approximated",
                "rtl_shaping",
                "writingDirection=rtl set; bidi shaping delegated to diagrams.net",
            )
        )
    return build_capability_report("drawio", supports, warnings)
