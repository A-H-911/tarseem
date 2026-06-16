"""tools/build_review.py must FAIL LOUDLY on a locked file, not silently skip it.

A locked target (an open .pptx in PowerPoint / .drawio in diagrams.net) keeps its OLD contents;
a silent skip makes a stale preview look freshly regenerated — which once masked a real fix.
"""
from __future__ import annotations

import sys
from pathlib import Path

_TOOLS = Path(__file__).resolve().parent.parent / "tools"
sys.path.insert(0, str(_TOOLS))

import build_review  # noqa: E402


def _raise(exc: Exception):
    def fn() -> None:
        raise exc

    return fn


def test_safe_records_a_locked_file():
    locked: list[str] = []
    status = build_review._safe(_raise(PermissionError("open in PowerPoint")), "x.pptx", locked)
    assert status == "locked"
    assert locked == ["x.pptx"]


def test_safe_does_not_mark_success_or_render_errors_as_locked():
    locked: list[str] = []
    assert build_review._safe(lambda: None, "ok.svg", locked) is None
    # a render error is best-effort (warning), NOT a stale-file lock
    assert build_review._safe(_raise(ValueError("render fail")), "y.png", locked) == "render fail"
    assert locked == []
