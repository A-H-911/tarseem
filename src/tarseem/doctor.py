"""`engine doctor` (A11): verify runtime dependencies with actionable failures.

Checks the four things a render needs and that ``engine doctor`` must keep verifying:
Node runtime, the pinned vendored elkjs bundle, Playwright's Chromium, and the bundled
fonts. Each check returns ok/fail with a one-line, actionable hint — never a bare
"something is wrong". Checkers accept injected paths so failure modes are testable.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from tarseem.layout.elk._server import vendored_bundle
from tarseem.measure import default_font_path

__all__ = [
    "CheckResult",
    "DoctorReport",
    "check_node",
    "check_elkjs",
    "check_playwright_chromium",
    "check_fonts",
    "check_arabic_shaping",
    "check_raqm",
    "run_doctor",
]

# A diacritized word that only renders correctly when joining + mark positioning work.
_SHAPE_PROBE = "مقدّم"

PINNED_ELKJS = "0.11.1"


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str
    hint: str = ""

    def to_dict(self) -> dict:
        return {"name": self.name, "ok": self.ok, "detail": self.detail, "hint": self.hint}


@dataclass
class DoctorReport:
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(c.ok for c in self.checks)

    def to_dict(self) -> dict:
        return {"ok": self.ok, "checks": [c.to_dict() for c in self.checks]}


def check_node(node: str = "node") -> CheckResult:
    if shutil.which(node) is None:
        return CheckResult(
            "node", False, f"{node!r} not found on PATH",
            hint="install Node.js >= 18 and ensure it is on PATH",
        )
    try:
        proc = subprocess.run(
            [node, "--version"], capture_output=True, text=True, timeout=10, check=True
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return CheckResult(
            "node", False, f"failed to run {node!r}: {exc}",
            hint="reinstall Node.js; verify `node --version` works in a shell",
        )
    return CheckResult("node", True, f"Node {proc.stdout.strip()}")


def check_elkjs(bundle: Path | None = None) -> CheckResult:
    path = Path(bundle) if bundle is not None else vendored_bundle()
    if not path.exists():
        return CheckResult(
            "elkjs", False, f"vendored bundle missing at {path}",
            hint="reinstall tarseem; the pinned elkjs bundle ships inside the package",
        )
    pkg = path.parent.parent / "package.json"
    version = "unknown"
    try:
        version = json.loads(pkg.read_text(encoding="utf-8")).get("version", "unknown")
    except OSError:
        pass
    if version != PINNED_ELKJS:
        return CheckResult(
            "elkjs", False, f"bundle version {version}, expected pinned {PINNED_ELKJS}",
            hint=f"restore the pinned elkjs {PINNED_ELKJS} bundle (determinism depends on it)",
        )
    return CheckResult("elkjs", True, f"elkjs {version} (pinned) at {path.name}")


def check_playwright_chromium() -> CheckResult:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return CheckResult(
            "playwright", False, "playwright not importable",
            hint="pip install playwright",
        )
    try:
        with sync_playwright() as p:
            exe = Path(p.chromium.executable_path)
    except Exception as exc:  # noqa: BLE001 - report any launch/driver error as actionable
        return CheckResult(
            "playwright", False, f"chromium not available: {exc}",
            hint="run: playwright install chromium",
        )
    if not exe.exists():
        return CheckResult(
            "playwright", False, f"chromium executable missing at {exe}",
            hint="run: playwright install chromium",
        )
    return CheckResult("playwright", True, f"Chromium at {exe.name}")


def check_fonts(font_path: Path | None = None) -> CheckResult:
    path = Path(font_path) if font_path is not None else default_font_path()
    if not path.exists():
        return CheckResult(
            "fonts", False, f"bundled font missing at {path}",
            hint="reinstall tarseem; bundled OFL fonts ship inside the package",
        )
    try:
        import uharfbuzz as hb

        hb.Face(hb.Blob.from_file_path(str(path)))
    except Exception as exc:  # noqa: BLE001 - a corrupt/unreadable font is actionable
        return CheckResult(
            "fonts", False, f"font at {path.name} failed to load: {exc}",
            hint="reinstall tarseem; the bundled font may be corrupted",
        )
    return CheckResult("fonts", True, f"Cairo font at {path.name}")


def check_arabic_shaping(font_path: Path | None = None) -> CheckResult:
    """Shape a diacritized Arabic probe with the bundled font via uharfbuzz: the bundled
    Cairo must cover Arabic and shaping must run (no .notdef, positive advance). This is
    the primary Arabic-correctness gate (07 §1)."""
    path = Path(font_path) if font_path is not None else default_font_path()
    try:
        import uharfbuzz as hb

        face = hb.Face(hb.Blob.from_file_path(str(path)))
        font = hb.Font(face)
        buf = hb.Buffer()
        buf.add_str(_SHAPE_PROBE)
        buf.guess_segment_properties()
        hb.shape(font, buf)
        gids = [info.codepoint for info in buf.glyph_infos]
        advance = sum(p.x_advance for p in buf.glyph_positions)
    except Exception as exc:  # noqa: BLE001 - any shaping failure is actionable
        return CheckResult(
            "arabic-shaping", False, f"shaping probe failed: {exc}",
            hint="reinstall tarseem; uharfbuzz + the bundled Cairo font are required",
        )
    if not gids or 0 in gids or advance <= 0:
        return CheckResult(
            "arabic-shaping", False,
            f"probe {_SHAPE_PROBE!r} produced gids={gids} advance={advance}",
            hint="the bundled font lacks Arabic coverage; restore the OFL Cairo build",
        )
    return CheckResult(
        "arabic-shaping", True, f"shaped {_SHAPE_PROBE!r} -> {len(gids)} glyphs (uharfbuzz)"
    )


def check_raqm() -> CheckResult:
    """Report Pillow+libraqm availability for the *optional* measurement cross-check.

    Informational only (always ``ok``): uharfbuzz is the primary measurer, so a missing
    libraqm — common on Windows — must not fail ``doctor``. It only disables the
    secondary cross-check (07 §1, R-3)."""
    try:
        from PIL import features

        available = bool(features.check("raqm"))
    except Exception as exc:  # noqa: BLE001 - Pillow missing -> cross-check simply off
        return CheckResult(
            "raqm", True, f"Pillow/raqm unavailable ({exc}); uharfbuzz is primary"
        )
    if available:
        return CheckResult("raqm", True, "Pillow+libraqm available (measurement cross-check on)")
    return CheckResult(
        "raqm", True, "libraqm not built into Pillow; uharfbuzz is primary (cross-check off)"
    )


def run_doctor() -> DoctorReport:
    """Run all dependency checks and return a structured report."""
    return DoctorReport(
        checks=[
            check_node(),
            check_elkjs(),
            check_playwright_chromium(),
            check_fonts(),
            check_arabic_shaping(),
            check_raqm(),
        ]
    )
