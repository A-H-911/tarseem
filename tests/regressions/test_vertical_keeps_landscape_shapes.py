"""Regression: vertical swimlanes flip the LANES, not the SHAPES (bug report #7).

The first vertical implementation transposed the whole diagram, swapping each node's width and
height so shapes rotated to portrait and overflowed the (too-narrow) columns. Vertical now has
its own placement: lanes are columns relaxed to the widest node, the flow runs top->bottom, and
node boxes keep the same landscape dimensions they have in a horizontal swimlane.
"""
from __future__ import annotations

from tarseem.layout.lanegrid import LaneGridLayout
from tarseem.measure import measure_graph
from tarseem.model import compile_spec

VSPEC = {
    "specVersion": "1.0", "diagramType": "swimlane", "direction": "TB",
    "meta": {"title": "Release"}, "layout": {"laneOrientation": "vertical"},
    "lanes": [{"id": "dev", "label": {"text": "Dev"}}, {"id": "ci", "label": {"text": "CI"}},
              {"id": "ops", "label": {"text": "Ops"}}],
    "nodes": [
        {"id": "commit", "lane": "dev", "shape": "roundrect", "label": {"text": "Commit"}},
        {"id": "build", "lane": "ci", "shape": "roundrect", "label": {"text": "Build"}},
        {"id": "deploy", "lane": "ops", "shape": "roundrect", "label": {"text": "Deploy"}},
    ],
    "edges": [{"id": "e1", "source": "commit", "target": "build"},
              {"id": "e2", "source": "build", "target": "deploy"}],
}
HSPEC = {**VSPEC, "layout": {}}  # same diagram, horizontal


def _layout(spec):
    return LaneGridLayout().layout(measure_graph(compile_spec(spec)))


def test_nodes_keep_landscape_dimensions():
    v = {n.id: n for n in _layout(VSPEC).nodes}
    h = {n.id: n for n in _layout(HSPEC).nodes}
    for nid in ("commit", "build", "deploy"):
        assert v[nid].width > v[nid].height  # landscape, NOT rotated to portrait
        # identical box size to the horizontal swimlane (shapes unchanged, only lanes flipped)
        assert (v[nid].width, v[nid].height) == (h[nid].width, h[nid].height)


def test_lane_columns_are_relaxed_to_fit_the_landscape_node():
    d = _layout(VSPEC)
    bands = {b.id: b for b in d.lanes}
    for n in d.nodes:
        band = bands[next(x["lane"] for x in VSPEC["nodes"] if x["id"] == n.id)]
        assert band.width > n.width  # the column is wider than the node it holds (relaxed)
        assert band.height > band.width  # ... and it is a column, not a row


def test_flow_runs_top_to_bottom():
    y = {n.id: n.y for n in _layout(VSPEC).nodes}
    assert y["commit"] < y["build"] < y["deploy"]
