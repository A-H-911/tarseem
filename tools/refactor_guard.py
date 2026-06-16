"""Refactor guard (throwaway dev tool): same-environment before/after behavior check.

Renders every ``examples/*.json`` to SVG string, draw.io XML, and PPTX slide XML, strips the
non-geometry noise (the embedded font data-URI; PPTX carries no timestamp in slide XML), and
records a sha256 per ``(example, format)``. ``capture`` records a baseline (gitignored);
``check`` diffs the current output against it. Any hash change = behavior changed.

NOT a committed golden: the embedded woff2 subset (fonttools/brotli), the zip bytes
(python-pptx/zlib), and even the *coordinates* (uharfbuzz text measurement) are not reproducible
across dependency/OS versions — so this guard is only valid within ONE venv/session, which is
exactly what a behavior-preserving refactor needs. Usage:

    .venv/Scripts/python.exe tools/refactor_guard.py capture   # at branch point
    .venv/Scripts/python.exe tools/refactor_guard.py check     # after each stage
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"
BASELINE = ROOT / ".refactor_guard_baseline.json"

# Strip the embedded font subset (fonttools/brotli-dependent) so the hash reflects only
# coordinates/markup — exactly what this refactor can change.
_SVG_FONT = re.compile(r'(data:font/woff2;base64,)[^)"]*')
_DRAWIO_FONT = re.compile(r"(fontSource=)[^;]*")


def _h(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _render_all() -> tuple[dict[str, str], list[str]]:
    from pptx import Presentation

    from tarseem import Engine
    from tarseem.export.drawio import to_drawio_xml
    from tarseem.export.pptx import to_pptx_bytes

    hashes: dict[str, str] = {}
    errors: list[str] = []
    for spec_path in sorted(EXAMPLES.glob("*.json")):
        name = spec_path.stem
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        try:
            result = Engine().render(spec)
        except Exception as e:  # noqa: BLE001 - defensive: log + skip, never abort the sweep
            errors.append(f"{name}::render: {type(e).__name__}: {e}")
            continue
        try:
            hashes[f"{name}::svg"] = _h(_SVG_FONT.sub(r"\1<STRIPPED>", result.svg))
        except Exception as e:  # noqa: BLE001
            errors.append(f"{name}::svg: {type(e).__name__}: {e}")
        try:
            xml = to_drawio_xml(result.diagram)
            hashes[f"{name}::drawio"] = _h(_DRAWIO_FONT.sub(r"\1<STRIPPED>", xml))
        except Exception as e:  # noqa: BLE001
            errors.append(f"{name}::drawio: {type(e).__name__}: {e}")
        try:
            prs = Presentation(io.BytesIO(to_pptx_bytes(result.diagram)))
            hashes[f"{name}::pptx"] = _h(prs.slides[0]._element.xml)
        except Exception as e:  # noqa: BLE001
            errors.append(f"{name}::pptx: {type(e).__name__}: {e}")
    return hashes, errors


def capture() -> int:
    hashes, errors = _render_all()
    BASELINE.write_text(
        json.dumps({"hashes": hashes, "errors": errors}, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    examples = {k.split("::")[0] for k in hashes}
    print(f"captured {len(hashes)} hashes across {len(examples)} examples -> {BASELINE.name}")
    for e in errors:
        print(f"  (excluded) {e}")
    return 0


def check() -> int:
    if not BASELINE.exists():
        print("no baseline; run `capture` first", file=sys.stderr)
        return 2
    before = json.loads(BASELINE.read_text(encoding="utf-8"))["hashes"]
    now, _ = _render_all()
    changed = sorted(k for k in before if k in now and before[k] != now[k])
    missing = sorted(k for k in before if k not in now)
    added = sorted(k for k in now if k not in before)
    if not (changed or missing or added):
        print(f"OK - {len(now)} hashes unchanged (behavior preserved)")
        return 0
    print("BEHAVIOR CHANGED:")
    for k in changed:
        print(f"  ~ {k}")
    for k in missing:
        print(f"  - {k} (now errors/absent)")
    for k in added:
        print(f"  + {k} (new)")
    return 1


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    raise SystemExit({"capture": capture, "check": check}.get(cmd, check)())
