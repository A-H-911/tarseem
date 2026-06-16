"""Regression: ELK radial overlapped nodes on deep/uneven mindmap trees (C1b/C1c piled onto the
nodes beneath them). Fixed by a deterministic overlap-removal post-pass
(``tarseem.layout.radial.remove_radial_overlaps``) applied to radial mindmaps: it nudges
overlapping pairs apart along their least-penetration axis (staying compact — a naive global
rescale blew a 14-node map up ~8x), guaranteeing zero node overlaps. mrtree never overlaps (the
default is unaffected); a balanced radial map has no real overlap and passes through untouched.
"""
from __future__ import annotations

import shutil

import pytest

from tarseem import Engine
from tarseem.layout.radial import remove_radial_overlaps
from tarseem.model.ir import Label, LogicalEdge, LogicalGraph, PositionedDiagram, PositionedNode

requires_node = pytest.mark.skipif(shutil.which("node") is None, reason="ELK layout needs Node")


def _deep_spec() -> dict:
    # root + 10 children + a 3-deep chain + two small sub-trees: the shape radial overlaps on.
    edges = ([("Root", f"C{i}") for i in range(1, 11)]
             + [("C1", "C1a"), ("C1a", "C1b"), ("C1b", "C1c"),
                ("C2", "C2a"), ("C2", "C2b"), ("C3", "C3a")])
    ids: list[str] = []
    for s, t in edges:
        for nid in (s, t):
            if nid not in ids:
                ids.append(nid)
    return {
        "specVersion": "1.0", "diagramType": "mindmap", "layout": {"mindmapStyle": "radial"},
        "nodes": [{"id": n, "label": {"text": n}} for n in ids],
        "edges": [{"source": s, "target": t} for s, t in edges],
    }


def _overlaps(nodes) -> int:
    boxes = [(n.x, n.y, n.width, n.height) for n in nodes]
    c = 0
    for i in range(len(boxes)):
        ax, ay, aw, ah = boxes[i]
        for j in range(i + 1, len(boxes)):
            bx, by, bw, bh = boxes[j]
            if ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah:
                c += 1
    return c


# ---- integration: through the real ELK radial layout -------------------------
@requires_node
def test_deep_radial_has_no_node_overlaps():
    d = Engine().render(_deep_spec()).diagram
    assert _overlaps(d.nodes) == 0  # the post-pass guarantees separation


@requires_node
def test_deep_radial_stays_compact():
    # the fix must not blow the map up (a uniform rescale made the same map ~4690px wide).
    d = Engine().render(_deep_spec()).diagram
    assert d.width < 1200 and d.height < 1200


@requires_node
def test_deep_radial_is_deterministic():
    a = Engine().render(_deep_spec()).diagram
    b = Engine().render(_deep_spec()).diagram
    coords = lambda d: [(n.id, round(n.x, 3), round(n.y, 3)) for n in d.nodes]  # noqa: E731
    assert coords(a) == coords(b)


# ---- unit: the post-pass itself (pure, no Node) ------------------------------
def _node(nid: str, x: float, y: float) -> PositionedNode:
    return PositionedNode(id=nid, x=x, y=y, width=80.0, height=40.0,
                          label=Label(text=nid), shape="roundrect")


def _graph(*edges: tuple[str, str]) -> LogicalGraph:
    return LogicalGraph(diagram_type="mindmap",
                        edges=tuple(LogicalEdge(id=f"{s}->{t}", source=s, target=t)
                                    for s, t in edges))


def test_post_pass_separates_overlapping_boxes():
    root, a, b = _node("r", 200, 200), _node("a", 0, 0), _node("b", 20, 10)  # a,b overlap
    diagram = PositionedDiagram(width=300, height=300, nodes=(root, a, b), edges=(),
                                diagram_type="mindmap")
    out = remove_radial_overlaps(diagram, _graph(("r", "a"), ("r", "b")))
    assert _overlaps(out.nodes) == 0


def test_post_pass_is_noop_when_nothing_overlaps():
    root, a, b = _node("r", 0, 0), _node("a", 200, 0), _node("b", 0, 200)  # all disjoint
    diagram = PositionedDiagram(width=400, height=400, nodes=(root, a, b), edges=(),
                                diagram_type="mindmap")
    out = remove_radial_overlaps(diagram, _graph(("r", "a"), ("r", "b")))
    assert out is diagram  # early-return: a clean map is returned untouched (no churn)


def test_post_pass_is_deterministic():
    def run():
        root, a, b = _node("r", 200, 200), _node("a", 0, 0), _node("b", 18, 12)
        d = PositionedDiagram(width=300, height=300, nodes=(root, a, b), edges=(),
                              diagram_type="mindmap")
        return remove_radial_overlaps(d, _graph(("r", "a"), ("r", "b")))

    one, two = run(), run()
    assert [(n.id, n.x, n.y) for n in one.nodes] == [(n.id, n.x, n.y) for n in two.nodes]
