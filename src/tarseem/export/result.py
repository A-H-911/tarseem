"""``WriteResult``: the uniform return type of every export writer.

Each writer returns the path it wrote plus a ``CapabilityReport`` declaring what it could and
could not carry (invariant 6). ``RenderResult.export`` collects these so the caller — and the
Phase-6 fidelity table — sees fidelity per artifact, never a silent drop.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tarseem.report import CapabilityReport

__all__ = ["WriteResult"]


@dataclass(frozen=True)
class WriteResult:
    path: Path
    report: CapabilityReport
