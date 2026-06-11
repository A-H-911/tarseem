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
import sys
from pathlib import Path

from tarseem.engine import Engine

# Node-free families only (lane-grid + sequence layouters) -> hermetic, deterministic.
BASELINE_SAMPLES = [
    "sequence-login",
    "swimlane-bug-triage",
    "swimlane-pipeline",
    "swimlane-phases",
]

ROOT = Path(__file__).resolve().parent.parent


def baseline_dir(platform: str | None = None) -> Path:
    return ROOT / "tests" / "baselines" / (platform or sys.platform)


def regen() -> list[Path]:
    out_dir = baseline_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    engine = Engine()
    written: list[Path] = []
    for name in BASELINE_SAMPLES:
        spec = json.loads((ROOT / "examples" / f"{name}.json").read_text(encoding="utf-8"))
        res = engine.render(spec)
        paths = res.export(["png"], out_dir, name)
        written.append(paths["png"])
        print(f"baseline: {paths['png']}")
    return written


if __name__ == "__main__":
    regen()
    print(f"\nwrote {len(BASELINE_SAMPLES)} baselines for platform '{sys.platform}'.")
