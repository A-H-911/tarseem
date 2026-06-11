"""Reference-fidelity contract for swimlanes (⚠4 / A12).

The acceptance references (docs/plan/references/) are draw.io exports, so a *pixel* match
is the wrong gate — Tarseem owns its renderer and style. What must hold is the *structural*
visual contract from references/analysis.md: the lanes, the reference shape set, UML
markers, numbered badges (start/terminal exempt), cross-lane back-edges, per-lane hue
tints, and a title bar. This test encodes that checklist as assertions so Ref-1 (Bug
Triage) and Ref-3 (Pipeline) fidelity is verified automatically, not by eye.
"""
from __future__ import annotations

from pathlib import Path

from tarseem.layout.lanegrid import LaneGridLayout
from tarseem.measure import measure_graph
from tarseem.model import compile_spec
from tarseem.render import render_svg
from test_a12_swimlane import BUG_TRIAGE, PIPELINE

ROOT = Path(__file__).resolve().parent.parent
REFERENCES = ROOT / "docs" / "plan" / "references"


def _layout(spec):
    return LaneGridLayout().layout(measure_graph(compile_spec(spec)))


def _has_back_edge(d) -> bool:
    """A back-edge enters a node in an earlier column: its routed polyline ends left of
    where it started. Marker connector edges are excluded."""
    for e in d.edges:
        if e.id.startswith("__marker"):
            continue
        if len(e.points) >= 2 and e.points[-1][0] < e.points[0][0]:
            return True
    return False


# ---- Reference-1: Bug Triage ------------------------------------------------
def test_bug_triage_matches_reference_contract():
    d = _layout(BUG_TRIAGE)
    assert (REFERENCES / "reference-1-bug-triage-ltr.png").exists()  # the visual target

    assert d.title == "Bug Triage"  # title bar
    assert [b.label.text for b in d.lanes] == [
        "Reporter", "Triage Engineer", "Developer", "QA"
    ]
    shapes = {n.shape for n in d.nodes}
    assert {"stadium", "roundrect", "diamond"} <= shapes  # reference shape subset
    assert d.markers == ()  # Ref-1 has no UML start/end markers

    badge = {n.id: n.badge for n in d.nodes}
    assert badge["report"] is None and badge["close"] is None  # terminals exempt
    assert badge["classify"] == "2."  # numbered by column

    assert _has_back_edge(d)  # verify -> fix loops back across lanes
    fills = {n.id: n.style.get("fill") for n in d.nodes}
    assert fills["report"] != fills["classify"]  # per-lane hue tints differ


# ---- Reference-3: Pipeline --------------------------------------------------
def test_pipeline_matches_reference_contract():
    d = _layout(PIPELINE)
    assert (REFERENCES / "reference-3-pipeline-shapes.png").exists()

    assert d.title == "Pipeline"
    assert [b.label.text for b in d.lanes] == ["User", "System", "Storage"]

    shapes = {n.shape for n in d.nodes}
    assert {"parallelogram", "diamond", "roundrect", "cylinder", "document"} <= shapes
    assert {m.kind for m in d.markers} == {"start", "end"}  # UML markers present

    svg = render_svg(d)
    assert "stroke-dasharray" in svg  # the dashed async edge
    assert _has_back_edge(d)  # validate -> upload loops back
