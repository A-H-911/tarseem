"""Regression: a back-edge routed through (and its label sat on) an intervening node.

Reported bug (showcase release pipeline): the "rework" back-edge from a later column to an
earlier one ran its horizontal segment along the target lane's node row, passing straight
*through* the "Unit tests" box (hidden, since nodes paint over edges) and placing its label
on that box.

Root cause was the layout layer (lanegrid routing): the direct 3-point L-route had no
obstacle awareness. Fixed two ways, both pure-Python (not an upstream limitation):
1. routing — when the direct route would cross an intervening node, detour through a
   node-free corridor below/above all nodes, leaving and re-entering the endpoints
   vertically (south-to-south / north-to-north). Direct routes that are already clear are
   unchanged, so existing baselines do not move.
2. label placement — put the label at the polyline point nearest the midpoint whose
   background box clears every node (defence in depth; a no-op once routing avoids nodes).

This locks (a) no swimlane edge segment crossing an intervening node and (b) no edge label
overlapping a node.
"""
from __future__ import annotations

import json
from pathlib import Path

from tarseem.engine import Engine

HERE = Path(__file__).resolve().parent
# matches the swimlane renderer's label-box geometry
_HH, _MARGIN = 9.0, 2.0


def _edge_st(spec: dict) -> dict:
    return {e.get("id", f"{e['source']}->{e['target']}"): (e["source"], e["target"])
            for e in spec.get("edges", [])}


def _seg_crosses(p, q, box) -> bool:
    x0, y0, x1, y1 = box
    if abs(p[1] - q[1]) < 1e-6:  # horizontal
        y = p[1]
        lo, hi = sorted((p[0], q[0]))
        return y0 < y < y1 and x0 < hi and x1 > lo
    x = p[0]  # vertical
    lo, hi = sorted((p[1], q[1]))
    return x0 < x < x1 and y0 < hi and y1 > lo


def _crossed_nodes(edge, src, tgt, boxes_by_id) -> set:
    crossed: set = set()
    for i in range(len(edge.points) - 1):
        for nid, box in boxes_by_id.items():
            if nid in (src, tgt):
                continue
            if _seg_crosses(edge.points[i], edge.points[i + 1], box):
                crossed.add(nid)
    return crossed


def _half_w(text: str) -> float:
    return max(10.0, len(text) * 3.6)


def _overlaps(cx, cy, hw, box) -> bool:
    x0, y0, x1, y1 = box
    return (cx + hw + _MARGIN > x0 and cx - hw - _MARGIN < x1
            and cy + _HH + _MARGIN > y0 and cy - _HH - _MARGIN < y1)


def test_backedge_routes_around_intervening_node():
    spec = json.loads((HERE / "backedge_label_over_node.json").read_text(encoding="utf-8"))
    d = Engine().render(spec).diagram
    boxes_by_id = {n.id: (n.x, n.y, n.x + n.width, n.y + n.height) for n in d.nodes}
    st = _edge_st(spec)
    rework = next(e for e in d.edges if e.label and e.label.text == "rework")
    src, tgt = st[rework.id]
    assert not _crossed_nodes(rework, src, tgt, boxes_by_id), "rework edge crosses a node"
    # and it leaves the diamond from the south and enters compile from the south
    gate = boxes_by_id["gate"]
    assert abs(rework.points[0][1] - gate[3]) < 1.0  # starts at gate's bottom edge
    compile_box = boxes_by_id["compile"]
    assert abs(rework.points[-1][1] - compile_box[3]) < 1.0  # ends at compile's bottom edge


def test_no_swimlane_edge_crosses_an_intervening_node():
    root = HERE.parent.parent
    for name in ["swimlane-bug-triage", "swimlane-pipeline", "swimlane-document-rtl"]:
        spec = json.loads((root / "examples" / f"{name}.json").read_text(encoding="utf-8"))
        d = Engine().render(spec).diagram
        boxes_by_id = {n.id: (n.x, n.y, n.x + n.width, n.y + n.height) for n in d.nodes}
        st = _edge_st(spec)
        for e in d.edges:
            if e.id not in st:
                continue
            src, tgt = st[e.id]
            assert not _crossed_nodes(e, src, tgt, boxes_by_id), \
                f"{name}: edge {e.id} crosses intervening node(s)"


def test_backedge_label_clears_intervening_node():
    spec = json.loads((HERE / "backedge_label_over_node.json").read_text(encoding="utf-8"))
    d = Engine().render(spec).diagram
    boxes = [(n.x, n.y, n.x + n.width, n.y + n.height) for n in d.nodes]
    rework = next(e for e in d.edges if e.label and e.label.text == "rework")
    assert rework.label_xy is not None
    lx, ly = rework.label_xy
    hw = _half_w("rework")
    hits = [i for i, b in enumerate(boxes) if _overlaps(lx, ly, hw, b)]
    assert not hits, f"rework label at ({lx:.0f},{ly:.0f}) still overlaps node box(es) {hits}"


def test_every_swimlane_edge_label_clears_nodes():
    # generalise across the committed swimlane corpus: no edge label may sit on a node
    root = HERE.parent.parent
    for name in ["swimlane-bug-triage", "swimlane-pipeline", "swimlane-document-rtl"]:
        spec = json.loads((root / "examples" / f"{name}.json").read_text(encoding="utf-8"))
        d = Engine().render(spec).diagram
        boxes = [(n.x, n.y, n.x + n.width, n.y + n.height) for n in d.nodes]
        for e in d.edges:
            if e.label and e.label.text and e.label_xy:
                lx, ly = e.label_xy
                hw = _half_w(e.label.text)
                hits = [i for i, b in enumerate(boxes) if _overlaps(lx, ly, hw, b)]
                assert not hits, f"{name}: '{e.label.text}' label overlaps node {hits}"
