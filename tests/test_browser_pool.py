"""Shared Chromium pool (render.browser): reuse one browser, recover from crashes, no leaks.

These guard the perf fix that stopped launching Chromium per rasterization. They mutate the
process-wide pool (shutdown/relaunch), which is safe because the pool is lazy and re-inits on next
use. Chromium-gated: skip cleanly when no browser is installed.
"""
from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path

import pytest

import tarseem.render.browser as pool
from tarseem.engine import Engine
from tarseem.export import svg_to_png

requires_chromium = pytest.mark.skipif(
    pool.chromium_executable() is None, reason="Chromium unavailable"
)

_SVG_A = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="40" height="20">'
    '<rect width="40" height="20" fill="#abc"/></svg>'
)


def _node_free_svg(name: str) -> str:
    spec = json.loads(Path(f"examples/{name}.json").read_text(encoding="utf-8"))
    return Engine().render(spec).svg  # swimlane/sequence use the pure-Python layouter (no Node)


pytestmark = requires_chromium


def test_browser_launched_once_across_n_rasters(tmp_path, monkeypatch):
    pool.shutdown()  # clean slate
    assert pool.chromium_executable() is not None  # ensures the driver is started
    calls = {"n": 0}
    real_launch = pool._PW.chromium.launch  # type: ignore[union-attr]

    def counting_launch(*a, **k):
        calls["n"] += 1
        return real_launch(*a, **k)

    monkeypatch.setattr(pool._PW.chromium, "launch", counting_launch)  # type: ignore[union-attr]
    for i in range(3):
        svg_to_png(_SVG_A, tmp_path / f"{i}.png")
    assert calls["n"] == 1  # launched once, reused for the other two


def test_png_first_and_third_render_identical(tmp_path):
    """A,B,A: a render of a different diagram in between must not bleed state into the shared
    browser — the 1st and 3rd renders of the same SVG stay byte-identical."""
    a1 = svg_to_png(_node_free_svg("swimlane-pipeline"), tmp_path / "a1.png").read_bytes()
    svg_to_png(_node_free_svg("swimlane-phases"), tmp_path / "b.png")
    a2 = svg_to_png(_node_free_svg("swimlane-pipeline"), tmp_path / "a2.png").read_bytes()
    assert hashlib.sha256(a1).hexdigest() == hashlib.sha256(a2).hexdigest()


def test_render_error_does_not_poison_pool(tmp_path):
    with pytest.raises(RuntimeError):
        svg_to_png("<div>not an svg</div>", tmp_path / "bad.png")
    # the browser survives; a good render still works
    out = svg_to_png(_SVG_A, tmp_path / "good.png")
    assert out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_pool_relaunches_after_disconnect(tmp_path):
    svg_to_png(_SVG_A, tmp_path / "warm.png")
    first = pool.shared_browser()
    first.close()  # force a disconnect
    assert not first.is_connected()
    svg_to_png(_SVG_A, tmp_path / "after.png")  # must relaunch transparently
    second = pool.shared_browser()
    assert second.is_connected() and second is not first


def test_pages_do_not_accumulate(tmp_path):
    for i in range(4):
        svg_to_png(_SVG_A, tmp_path / f"p{i}.png")
    # new_page() creates an owned context that page.close() also closes -> none linger
    assert len(pool.shared_browser().contexts) == 0


def test_shutdown_is_idempotent():
    svg_to_png(_SVG_A, Path.cwd() / "_pool_probe.png")  # ensure something is up
    Path("_pool_probe.png").unlink(missing_ok=True)
    pool.shutdown()
    pool.shutdown()  # second call must not raise
    assert pool._BROWSER is None and pool._PW is None


def test_thread_guard_raises():
    pool.shutdown()
    assert pool.chromium_executable() is not None  # binds the pool to THIS (main) thread
    err: dict[str, BaseException | None] = {"exc": None}

    def use_from_other_thread():
        try:
            pool.shared_browser()
        except BaseException as e:  # noqa: BLE001 - capture whatever is raised
            err["exc"] = e

    t = threading.Thread(target=use_from_other_thread)
    t.start()
    t.join()
    assert isinstance(err["exc"], RuntimeError)
