"""Agent surface (F11): one ``generate(spec) -> artifacts + report`` call for tools/LLMs.

Design contract:

- **Pure-ish + never raises for spec problems.** A spec error comes back as a JSON payload
  ``{"ok": false, "errors": [{code, path, message, hint, severity}], "warnings": [...]}`` —
  the machine-actionable contract agents repair against (05 §5, R-28), not an exception.
- **SVG by default, returned inline.** The canonical SVG is pure Python (no browser), so the
  common "give me the diagram" call needs no filesystem and no Chromium.
- **Raster is always subprocessed.** PNG/PDF need the process-wide *sync* Chromium pool, which
  cannot start inside a running asyncio event loop. So whenever a raster format is requested,
  ``generate`` runs the whole export in a fresh ``python -m tarseem.agent`` subprocess — safe
  from any caller context (sync or async). draw.io/PPTX are pure-Python file writers and run
  in-process. (See the raster-Chromium-pool note in the engine docs.)
- **File formats need ``out_dir``.** SVG is inline; png/pdf/drawio/pptx are written as files,
  so they require an output directory. Every written artifact's path is returned.
"""
from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path

from tarseem.errors import SpecValidationError, ValidationResult
from tarseem.validation import validate

__all__ = ["generate"]

# Formats whose writer drives the Chromium pool -> must run in a subprocess from the agent surface.
_RASTER = frozenset({"png", "pdf"})
# Formats written to disk (everything but the inline SVG) -> require out_dir.
_FILE_FORMATS = frozenset({"png", "pdf", "drawio", "pptx"})


def _normalize_formats(formats: str | Iterable[str]) -> list[str]:
    items = formats.split(",") if isinstance(formats, str) else list(formats)
    out = [f.strip() for f in items if f and f.strip()]
    return out or ["svg"]


def _error(code: str, message: str, hint: str, warnings: list[dict] | None = None) -> dict:
    return {
        "ok": False,
        "errors": [{"code": code, "path": "/", "message": message, "hint": hint,
                    "severity": "error"}],
        "warnings": warnings or [],
    }


def _validation_payload(result: ValidationResult) -> dict:
    return {
        "ok": False,
        "errors": [e.to_dict() for e in result.errors],
        "warnings": [w.to_dict() for w in result.warnings],
    }


def generate(
    spec: dict,
    formats: str | Iterable[str] = ("svg",),
    out_dir: str | Path | None = None,
    name: str = "diagram",
    node: str = "node",
) -> dict:
    """Render ``spec`` and return a JSON-serializable ``{ok, svg, artifacts, report, ...}``.

    Never raises for a bad spec — returns ``{"ok": false, "errors": [...]}`` instead, so an
    agent can read the coded/path-precise errors and self-repair.
    """
    fmts = _normalize_formats(formats)
    vr = validate(spec)
    if not vr.ok:
        return _validation_payload(vr)
    needs_dir = sorted(set(fmts) & _FILE_FORMATS)
    if needs_dir and out_dir is None:
        return _error(
            "E_OUTPUT",
            f"formats {needs_dir} are written to files and require out_dir",
            "pass out_dir=... (SVG is returned inline without it)",
            warnings=[w.to_dict() for w in vr.warnings],
        )
    if set(fmts) & _RASTER:
        return _run_subprocess(spec, fmts, str(out_dir), name, node)
    return _run_in_process(spec, fmts, out_dir, name, node)


def _run_subprocess(spec: dict, fmts: list[str], out_dir: str, name: str, node: str) -> dict:
    """Run the export in a fresh process so the sync Chromium pool never meets a caller's
    event loop. The child speaks the same JSON payload on stdout."""
    request = json.dumps(
        {"spec": spec, "formats": fmts, "out_dir": out_dir, "name": name, "node": node}
    )
    proc = subprocess.run(  # noqa: S603 - fixed argv, our own module, request via stdin
        [sys.executable, "-m", "tarseem.agent"],
        input=request,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if proc.returncode != 0:
        return _error("E_RENDER", "raster export subprocess failed",
                      (proc.stderr or "").strip()[-500:] or "no stderr")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return _error("E_RENDER", "could not parse export subprocess output",
                      (proc.stdout or "")[:500])


def _run_in_process(
    spec: dict, fmts: list[str], out_dir: str | Path | None, name: str, node: str
) -> dict:
    """The actual render + export + payload assembly. Also the subprocess entry point."""
    from tarseem.engine import Engine
    from tarseem.export.metadata import provenance

    try:
        result = Engine(node=node).render(spec)
    except SpecValidationError as exc:
        return _validation_payload(exc.result)
    except Exception as exc:  # noqa: BLE001 - surface any render failure as a coded error, never crash
        return _error(
            "E_RENDER", str(exc), "render failed; run `tarseem doctor` to check the toolchain"
        )

    payload: dict = {
        "ok": True,
        "diagramType": result.diagram.diagram_type,
        "svg": result.svg,
        "artifacts": {},
        "report": result.report.to_dict(),
        "capabilities": {},
        "warnings": [w.to_dict() for w in validate(spec).warnings],
        "provenance": provenance(result),
        "versions": result.versions,
    }
    if out_dir is not None:
        written = result.export(fmts, out_dir, name=name)
        payload["artifacts"] = {fmt: str(path) for fmt, path in written.items()}
        payload["capabilities"] = {fmt: rep.to_dict() for fmt, rep in result.reports.items()}
    return payload


def _main() -> None:
    """Subprocess entry (``python -m tarseem.agent``): a JSON request on stdin, a JSON payload
    on stdout. ASCII-escaped output so Windows consoles (cp1252) never choke on Arabic."""
    request = json.loads(sys.stdin.read())
    payload = _run_in_process(
        request["spec"], request["formats"], request["out_dir"],
        request.get("name", "diagram"), request.get("node", "node"),
    )
    sys.stdout.write(json.dumps(payload, ensure_ascii=True))


if __name__ == "__main__":
    _main()
