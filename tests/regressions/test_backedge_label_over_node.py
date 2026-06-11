"""Regression: a back-edge label overlapped an intervening same-lane node.

Reported bug (showcase release pipeline): the "rework" back-edge label sat on top of the
"Unit tests" box. The back-edge from a later column to an earlier one routes its horizontal
segment along the target lane's node row; its polyline *midpoint* — where the label is
placed — landed on a node sitting between source and target, so the label's white
background box collided with that node.

Root cause was the layout layer (lanegrid edge-label placement): the label was always put
at the geometric midpoint with no node-awareness. Fixed by placing the label at the
polyline point nearest the midpoint whose background box clears every node; the midpoint is
kept unchanged when already clear, so non-overlapping labels never move. (Not an upstream
limitation — the lane-grid router is pure Python.)

This locks every swimlane edge label clear of all node boxes.
"""
from __future__ import annotations

import json
from pathlib import Path

from tarseem.engine import Engine

HERE = Path(__file__).resolve().parent
# matches the swimlane renderer's label-box geometry
_HH, _MARGIN = 9.0, 2.0


def _half_w(text: str) -> float:
    return max(10.0, len(text) * 3.6)


def _overlaps(cx, cy, hw, box) -> bool:
    x0, y0, x1, y1 = box
    return (cx + hw + _MARGIN > x0 and cx - hw - _MARGIN < x1
            and cy + _HH + _MARGIN > y0 and cy - _HH - _MARGIN < y1)


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
