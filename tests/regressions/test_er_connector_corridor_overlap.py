"""Regression: ER relationship connectors leaving one entity must not share a vertical
corridor (bug report #1).

`_row_connector` always met at the midpoint between the facing edges, so two FK rows of the
same entity pointing at two entities in the same column produced identical corridors that
overlapped. Siblings are now fanned to ``(index+1)/(count+1)`` of the gap; a lone connector
stays centred.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from tarseem.layout.elk import _row_connector
from tarseem.model.ir import EntityRow, Label, PositionedNode

ROOT = Path(__file__).resolve().parent.parent.parent
requires_node = pytest.mark.skipif(
    shutil.which("node") is None, reason="Node.js runtime not on PATH (ELK layout)"
)


def _entity(nid: str, x: float, row_ids: list[str]) -> PositionedNode:
    rows = tuple(
        EntityRow(id=r, label=Label(text=r), y_offset=30 + 24 * i, height=24)
        for i, r in enumerate(row_ids)
    )
    return PositionedNode(id=nid, x=x, y=0, width=120, height=30 + 24 * len(row_ids),
                          label=Label(text=nid), shape="table", rows=rows)


# ---- _row_connector fan-out (no Node) ---------------------------------------
def test_single_connector_meets_at_the_midpoint():
    src = _entity("s", 0, ["k"])
    tgt = _entity("t", 300, ["id"])
    pts = _row_connector(src, "k", tgt, "id")  # count=1, index=0
    assert pts[1][0] == (src.x + src.width + tgt.x) / 2  # midpoint of the gap


def test_siblings_get_distinct_corridors():
    src = _entity("s", 0, ["k0", "k1"])
    tgt = _entity("t", 300, ["id"])
    c0 = _row_connector(src, "k0", tgt, "id", count=2, index=0)
    c1 = _row_connector(src, "k1", tgt, "id", count=2, index=1)
    assert c0[1][0] != c1[1][0]  # the two vertical corridors differ -> no overlap
    # both corridors lie strictly inside the gap
    gap = (src.x + src.width, tgt.x)
    assert gap[0] < c0[1][0] < gap[1] and gap[0] < c1[1][0] < gap[1]


# ---- end-to-end through ELK (Node-gated) ------------------------------------
@requires_node
def test_shop_fk_connectors_do_not_share_a_corridor():
    from tarseem.engine import Engine

    spec = json.loads((ROOT / "examples" / "er-shop.json").read_text(encoding="utf-8"))
    d = Engine().render(spec).diagram
    by_id = {e.id: e for e in d.diagram.edges} if hasattr(d, "diagram") else {
        e.id: e for e in d.edges}
    # r2 (OrderLine.order_id -> Order) and r3 (OrderLine.product_id -> Product) both leave
    # OrderLine's right side; their vertical corridors must differ.
    r2, r3 = by_id["r2"], by_id["r3"]
    assert r2.points[1][0] != r3.points[1][0]
