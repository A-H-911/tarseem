"""Phase 5 — crossing/overlap quality gated on a benchmark corpus.

The corpus = the golden ``examples/`` plus dense routing-stress specs in
``tests/benchmarks/``. For every sample we assert:

* **overlaps == 0** — a node-on-node overlap is always a hard failure.
* **crossings <= the per-sample budget** — budgets are the *currently measured*
  counts, so this is a ratchet: routing may improve and tighten a budget, but it
  can never silently regress past today's quality.

Running under pytest (which CI runs on the 3-OS matrix) makes this the CI gate the
phase plan calls for. ELK graph families need Node; swimlane/sequence are pure
Python and run everywhere.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from tarseem.engine import Engine

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"
BENCHMARKS = Path(__file__).resolve().parent / "benchmarks"

# Families whose layout runs through the ELK Node subprocess.
_ELK_FAMILIES = {"flowchart", "architecture", "dependency", "state", "deployment", "er"}

_HAS_NODE = shutil.which("node") is not None

# Per-sample crossing budget (max allowed). Default 0; only genuinely crossing-prone
# samples carry a non-zero ceiling, each justified by its structure.
_CROSSING_BUDGET: dict[str, int] = {
    "swimlane-bug-triage.json": 1,     # one unavoidable back-edge crossing
    "bench-dependency-web.json": 2,    # 14 edges over 8 nodes; dense by design
    "deployment-web-stack.json": 1,    # two app servers each share two datastores
    "er-shop.json": 1,                 # OrderLine fans out to two entities; one crossing
}


def _corpus() -> list[Path]:
    return sorted(EXAMPLES.glob("*.json")) + sorted(BENCHMARKS.glob("*.json"))


def _needs_node(spec: dict) -> bool:
    return spec.get("diagramType") in _ELK_FAMILIES


@pytest.mark.parametrize("path", _corpus(), ids=lambda p: p.name)
def test_sample_meets_routing_thresholds(path: Path) -> None:
    spec = json.loads(path.read_text(encoding="utf-8"))
    if _needs_node(spec) and not _HAS_NODE:
        pytest.skip("Node.js runtime not on PATH (ELK graph family)")

    report = Engine().render(spec).report
    budget = _CROSSING_BUDGET.get(path.name, 0)

    assert report.overlaps == 0, f"{path.name}: {report.overlaps} node overlap(s) (must be 0)"
    assert report.crossings <= budget, (
        f"{path.name}: {report.crossings} edge crossing(s) exceeds budget {budget} "
        f"(routing quality regressed)"
    )


def test_corpus_is_non_trivial() -> None:
    """Guard the gate itself: if the corpus silently empties, the parametrized test would
    vacuously pass. Require the dense benchmarks to be present."""
    names = {p.name for p in _corpus()}
    assert {"bench-cross-lane.json", "bench-dense-flow.json",
            "bench-dependency-web.json"} <= names
