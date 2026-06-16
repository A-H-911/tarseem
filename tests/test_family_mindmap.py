"""Mindmap family (Sub-stage 6): validate -> compile -> measure -> ELK (mrtree/radial) -> render.

Layout was de-risked by spike-6 (`docs/spikes/spike-6-report.md`): the pinned elkjs does
non-layered trees via `mrtree` (default) and `radial` (opt-in). mrtree is overlap-free on
deep/uneven trees; radial is offered for balanced maps only. Mindmap nodes are plain labelled
boxes (no chrome), so they reuse the generic render/writer path — only the layouter is new.
"""
from __future__ import annotations

import shutil

import pytest

from tarseem import Engine
from tarseem.layout.elk import ElkLayout
from tarseem.measure import measure_graph
from tarseem.model.compile import compile_spec
from tarseem.validation import validate

requires_node = pytest.mark.skipif(shutil.which("node") is None, reason="ELK layout needs Node")

# A deliberately DEEP/uneven tree (root + branches + a 3-deep chain) — the shape that makes
# radial overlap and that mrtree must still lay out cleanly (spike-6 finding).
SPEC = {
    "specVersion": "1.0",
    "diagramType": "mindmap",
    "direction": "LR",
    "nodes": [
        {"id": "Root", "label": {"text": "Roadmap"}},
        {"id": "A", "label": {"text": "Design"}},
        {"id": "B", "label": {"text": "Build"}},
        {"id": "C", "label": {"text": "Ship"}},
        {"id": "A1", "label": {"text": "Schema"}},
        {"id": "A2", "label": {"text": "Layout"}},
        {"id": "A1a", "label": {"text": "Validation"}},  # depth-3 chain Root->A->A1->A1a
        {"id": "B1", "label": {"text": "Renderers"}},
    ],
    "edges": [
        {"source": "Root", "target": "A"}, {"source": "Root", "target": "B"},
        {"source": "Root", "target": "C"}, {"source": "A", "target": "A1"},
        {"source": "A", "target": "A2"}, {"source": "A1", "target": "A1a"},
        {"source": "B", "target": "B1"},
    ],
}


def _overlaps(diagram) -> int:
    boxes = [(n.x, n.y, n.width, n.height) for n in diagram.nodes]
    n = 0
    for i in range(len(boxes)):
        ax, ay, aw, ah = boxes[i]
        for j in range(i + 1, len(boxes)):
            bx, by, bw, bh = boxes[j]
            if ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah:
                n += 1
    return n


def test_validate_accepts_mindmap_with_style_flag():
    assert validate({**SPEC, "layout": {"mindmapStyle": "radial"}}).ok


def test_validate_rejects_unknown_mindmap_style():
    assert not validate({**SPEC, "layout": {"mindmapStyle": "spiral"}}).ok


def test_compile_makes_plain_rounded_nodes_no_chrome():
    g = compile_spec(SPEC)
    root = next(n for n in g.nodes if n.id == "Root")
    assert root.shape == "roundrect"  # mindmap default shape
    assert root.rows == () and root.members == ()  # no ER/class chrome
    assert g.diagram_type == "mindmap"


def test_measure_sizes_mindmap_nodes():
    g = measure_graph(compile_spec(SPEC))
    assert all(n.width and n.height for n in g.nodes)


@requires_node
def test_capabilities_advertise_tree_algorithms():
    with ElkLayout() as elk:
        algos = elk.capabilities()["algorithms"]
    assert "mrtree" in algos and "radial" in algos


@requires_node
def test_mrtree_default_lays_out_deep_tree_without_overlap():
    diagram = Engine().render(SPEC).diagram
    assert len(diagram.nodes) == 8
    assert _overlaps(diagram) == 0, "mrtree must not overlap nodes on a deep/uneven tree"


@requires_node
@pytest.mark.parametrize("style", ["tree", "radial"])
def test_mindmap_layout_is_deterministic(style):
    # both shipped styles must be byte-stable across renders (invariant 7) — radial is shipped
    # now, so it is gated in the committed suite, not only by the per-OS baseline.
    spec = {**SPEC, "layout": {"mindmapStyle": style}}
    a = Engine().render(spec).diagram
    b = Engine().render(spec).diagram
    coords_a = sorted((n.id, round(n.x, 3), round(n.y, 3)) for n in a.nodes)
    coords_b = sorted((n.id, round(n.x, 3), round(n.y, 3)) for n in b.nodes)
    assert coords_a == coords_b, f"{style} mindmap layout must be deterministic"


@requires_node
def test_rtl_mindmap_mirrors_root_to_the_right():
    # RL -> mrtree elk.direction=LEFT: root anchors on the RIGHT, branches fan left (geometry-only
    # RTL mirroring, invariant 4). Verified visually with shaped Arabic (examples/mindmap-arabic).
    d = Engine().render({**SPEC, "direction": "RL"}).diagram
    xs = {n.id: n.x for n in d.nodes}
    assert xs["Root"] == max(xs.values()), "RTL mindmap root must be the rightmost node"


@requires_node
def test_radial_opt_in_produces_a_distinct_layout():
    tree = Engine().render(SPEC).diagram
    radial = Engine().render({**SPEC, "layout": {"mindmapStyle": "radial"}}).diagram
    assert len(radial.nodes) == len(tree.nodes)
    tree_xy = {n.id: (round(n.x), round(n.y)) for n in tree.nodes}
    radial_xy = {n.id: (round(n.x), round(n.y)) for n in radial.nodes}
    assert tree_xy != radial_xy  # the style flag actually changes the algorithm


@requires_node
def test_render_svg_has_all_labels_and_edges():
    svg = Engine().render(SPEC).svg
    for text in ("Roadmap", "Design", "Validation", "Renderers"):
        assert text in svg
    # each edge is one <path> (curved, with bends) or one <polyline> (straight) — 7 edges
    assert svg.count("<path") + svg.count("<polyline") >= 7
