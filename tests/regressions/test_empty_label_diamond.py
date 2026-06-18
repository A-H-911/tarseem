"""Regression: "diamond shape had no text" (activity merge node, 2026-06-18).

Reported as a render bug: a diamond in the activity sample showed no label. Investigation
(layer trace: validate -> compile -> measure -> layout -> render) found **no engine defect** —
the node's spec label was an empty string, and every layer faithfully carried it; a populated
diamond label renders intact. Root cause was the example spec authoring an empty-label "merge"
diamond, which reads like a dropped label.

These tests lock the engine behavior the investigation established: an empty spec label renders
as an empty shape (faithful, not a silent injection of placeholder text), and a populated label
is never dropped — for the diamond shape specifically. The misleading sample was fixed separately
(the redundant empty merge node was removed from examples/activity-order-approval.json).
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pytest

from tarseem.model import compile_spec
from tarseem.validation import validate

REPRO = Path("tests/regressions/empty_label_diamond.json")

requires_node = pytest.mark.skipif(
    shutil.which("node") is None, reason="Node.js runtime not on PATH (ELK graph families)"
)


def _spec() -> dict:
    return json.loads(REPRO.read_text(encoding="utf-8"))


def test_compile_carries_diamond_labels_faithfully():
    """The IR must keep an empty label empty and a populated label intact — no drop, no fill-in."""
    graph = compile_spec(_spec())
    by_id = {n.id: n for n in graph.nodes}
    assert validate(_spec()).ok
    assert by_id["empty"].shape == "diamond" and by_id["empty"].label.text == ""
    assert by_id["labeled"].shape == "diamond" and by_id["labeled"].label.text == "Has Text"


@requires_node
def test_render_emits_empty_text_for_empty_label_and_keeps_populated():
    """At the render layer: the empty-label diamond emits an empty <text>, the labeled one keeps
    its text. The 'missing text' is the empty spec label, never a dropped populated one."""
    from tarseem import Engine

    result = Engine().render(_spec())
    by_id = {n.id: n for n in result.diagram.nodes}
    assert by_id["empty"].label.text == ""  # faithful through layout
    assert by_id["labeled"].label.text == "Has Text"
    texts = re.findall(r"<text[^>]*>([^<]*)</text>", result.svg)
    assert "Has Text" in texts  # populated diamond label rendered
    assert "" in texts  # empty diamond label rendered as an empty element (not placeholder text)


@requires_node
def test_activity_sample_has_no_empty_label_control_diamond():
    """Guard the fix: the shipped activity sample must not carry an unlabeled merge diamond that
    reads as a bug (the redundant merge node was removed)."""
    spec = json.loads(Path("examples/activity-order-approval.json").read_text(encoding="utf-8"))
    empty_diamonds = [
        n["id"] for n in spec["nodes"]
        if n.get("shape") == "diamond" and not (n.get("label") or {}).get("text")
    ]
    assert empty_diamonds == [], f"unlabeled control diamonds in activity sample: {empty_diamonds}"
