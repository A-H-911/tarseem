"""Regenerate visual-regression baselines for the current platform.

Usage:  python scripts/regen_baselines.py

Baselines are OS-specific (Chromium font rasterization differs per platform), so they are
written under tests/baselines/<sys.platform>/. Regenerating is an explicit, reviewed action
(R-21): run this only when an intended visual change makes the diff legitimate, and review
the resulting PNG churn in the PR. Only the deterministic, Node-free families are baselined
here so the regression suite stays hermetic.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from tarseem.engine import Engine

# Node-free families (lane-grid + sequence layouters) -> hermetic, deterministic. Includes
# the RTL Arabic swimlane (Reference-2 rebuild), the Phase-4 pixel gate.
BASELINE_SAMPLES = [
    "sequence-login",
    "swimlane-bug-triage",
    "swimlane-pipeline",
    "swimlane-phases",
    "swimlane-document-rtl",
    "swimlane-vertical-release",  # Phase 5: vertical lanes
    "swimlane-nested-delivery",   # Phase 5: nested lanes
]

# ELK (graph) families need Node; deterministic via the pinned elkjs bundle, so they are
# baselined too — but only where Node is present (CI + the baselines workflow).
ELK_SAMPLES = [
    "arabic-flowchart",
    "arabic-architecture",
    "arabic-mixed",
    "state-order-lifecycle",   # Phase 5: state family
    "deployment-web-stack",    # Phase 5: deployment family
    "er-shop",                 # Phase 5: ER family
]

ROOT = Path(__file__).resolve().parent.parent


def baseline_dir(platform: str | None = None) -> Path:
    return ROOT / "tests" / "baselines" / (platform or sys.platform)


def _render_samples(names: list[str], out_dir: Path, engine: Engine) -> list[Path]:
    written: list[Path] = []
    for name in names:
        spec = json.loads((ROOT / "examples" / f"{name}.json").read_text(encoding="utf-8"))
        paths = engine.render(spec).export(["png"], out_dir, name)
        written.append(paths["png"])
        print(f"baseline: {paths['png']}")
    return written


def regen() -> list[Path]:
    out_dir = baseline_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    engine = Engine()
    written = _render_samples(BASELINE_SAMPLES, out_dir, engine)
    # ELK families only when Node + the vendored bundle are present
    from tarseem.layout.elk import elk_available

    if shutil.which("node") and elk_available():
        written += _render_samples(ELK_SAMPLES, out_dir, engine)
    else:
        print("skipping ELK Arabic baselines (Node/elkjs unavailable)")
    return written


if __name__ == "__main__":
    paths = regen()
    print(f"\nwrote {len(paths)} baselines for platform '{sys.platform}'.")
