"""Regression: `tarseem doctor` crashed on a cp1252 console (Windows) printing Arabic.

Reported via CI: every windows-latest job failed with UnicodeEncodeError. The doctor
arabic-shaping check detail includes the probe 'مقدّم'; Windows consoles default to cp1252,
which cannot encode Arabic, so the CLI raised mid-report (positions 30-34 = the 5 code
points of the probe).

Root cause was the render/export boundary — the CLI (`cli.main`) wrote to whatever encoding
the console used. Fixed by forcing UTF-8 stdio in the entrypoint (`_force_utf8_stdio`), so
Arabic in doctor/validate/spec output is safe on any platform. (Our own CLI, not upstream.)

This reproduces a cp1252-backed stdout cross-platform and asserts the CLI does not crash and
emits the Arabic probe as UTF-8.
"""
from __future__ import annotations

import io
import sys

from tarseem.cli import main


def test_doctor_does_not_crash_on_cp1252_stdout(monkeypatch):
    buf = io.BytesIO()
    cp1252 = io.TextIOWrapper(buf, encoding="cp1252", newline="")
    monkeypatch.setattr(sys, "stdout", cp1252)

    # Before the fix this raised UnicodeEncodeError (the probe 'مقدّم' is not cp1252-encodable).
    main(["doctor"])

    cp1252.flush()
    out = buf.getvalue().decode("utf-8")
    assert "مقدّم" in out  # Arabic survived as UTF-8 after the entrypoint reconfigured stdout
