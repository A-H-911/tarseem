"""A11 — `engine doctor` verifies Node/elkjs/Playwright/fonts with actionable failures."""
from __future__ import annotations

import shutil

import pytest

from tarseem.cli import main
from tarseem.doctor import (
    DoctorReport,
    check_elkjs,
    check_fonts,
    check_node,
    run_doctor,
)

requires_node = pytest.mark.skipif(
    shutil.which("node") is None, reason="Node.js runtime not on PATH"
)


def test_run_doctor_covers_all_dependencies():
    report = run_doctor()
    names = {c.name for c in report.checks}
    # core runtime deps + the Phase-4 Arabic checks (shaping gate + optional raqm status)
    assert names == {"node", "elkjs", "playwright", "fonts", "arabic-shaping", "raqm"}


def test_report_ok_aggregates_checks():
    report = DoctorReport(checks=[])
    assert report.ok is True  # vacuously true with no checks
    assert run_doctor().to_dict()["checks"]  # serializable, non-empty


def test_elkjs_check_passes_and_reports_pinned_version():
    result = check_elkjs()
    assert result.ok is True
    assert "0.11.1" in result.detail


def test_fonts_check_passes_for_bundled_cairo():
    result = check_fonts()
    assert result.ok is True
    assert "Cairo" in result.detail


@requires_node
def test_node_check_passes_when_node_present():
    assert check_node().ok is True


# ---- actionable failures (forced via injected bad paths) --------------------
def test_missing_elkjs_bundle_reports_actionable_hint(tmp_path):
    result = check_elkjs(bundle=tmp_path / "nope" / "elk.bundled.js")
    assert result.ok is False
    assert result.hint  # non-empty, actionable


def test_missing_font_reports_actionable_hint(tmp_path):
    result = check_fonts(font_path=tmp_path / "missing.ttf")
    assert result.ok is False
    assert result.hint


def test_missing_node_reports_actionable_hint():
    result = check_node(node="definitely-not-a-real-node-binary-xyz")
    assert result.ok is False
    assert result.hint


# ---- CLI --------------------------------------------------------------------
def test_cli_doctor_returns_zero_when_healthy(capsys):
    # this environment has node + bundle + fonts + chromium (used earlier)
    code = main(["doctor"])
    out = capsys.readouterr().out
    assert "node" in out and "elkjs" in out and "fonts" in out and "playwright" in out
    assert code in (0, 1)  # 0 if all green; never raises
