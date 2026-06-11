"""Browser E2E over the gallery (A6, 09 §1 browser-E2E row).

Builds the full example corpus into a static gallery and drives it in real Chromium via
Playwright: the index loads with zero console errors and one card per sample, and every
detail page renders an <svg> with no console errors and a resolvable SVG download. This is
the criterion-A6 gate ("all samples render error-free in Chromium").

Needs Node (graph families render via ELK) and a Playwright Chromium; skips cleanly if
either is missing so the unit suite still runs on a bare machine.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from tarseem.gallery import build_gallery

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = sorted((ROOT / "examples").glob("*.json"))

playwright = pytest.importorskip("playwright.sync_api", reason="playwright not installed")

requires_node = pytest.mark.skipif(
    shutil.which("node") is None, reason="Node.js runtime not on PATH (graph families)"
)


def _uri(path: Path) -> str:
    return path.resolve().as_uri()


@pytest.fixture(scope="module")
def gallery(tmp_path_factory):
    out = tmp_path_factory.mktemp("gallery")
    result = build_gallery(EXAMPLES, out, with_png=False)
    return out, result


@pytest.fixture(scope="module")
def browser():
    from playwright.sync_api import sync_playwright

    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            yield b
            b.close()
    except Exception as exc:  # noqa: BLE001 - chromium not installed -> skip the E2E layer
        pytest.skip(f"Chromium unavailable for E2E: {exc}")


def _console_errors(page) -> list[str]:
    errors: list[str] = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    return errors


@requires_node
def test_index_loads_error_free_with_a_card_per_sample(gallery, browser):
    out, result = gallery
    assert all(s.ok for s in result.samples), \
        f"samples failed to render: {[s.name for s in result.samples if not s.ok]}"
    page = browser.new_page()
    errors = _console_errors(page)
    page.goto(_uri(out / "index.html"))
    page.wait_for_load_state("networkidle")
    assert page.locator("a.card").count() == len(result.samples)
    assert errors == []
    page.close()


@requires_node
def test_every_detail_page_renders_svg_without_console_errors(gallery, browser):
    out, result = gallery
    for sample in result.samples:
        page = browser.new_page()
        errors = _console_errors(page)
        page.goto(_uri(out / f"{sample.name}.html"))
        page.wait_for_load_state("networkidle")
        assert page.locator("svg").count() >= 1, f"{sample.name}: no inline SVG"
        assert (out / "samples" / f"{sample.name}.svg").exists()  # download resolves
        assert errors == [], f"{sample.name}: console errors {errors}"
        page.close()
