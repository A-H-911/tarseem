"""Process-wide Chromium session — reuse one browser across rasterizations (perf).

Launching Chromium is a ~3 s cold start that spawns a whole process tree. ``png.py`` / ``pdf.py``
previously launched (and tore down) a browser **per call**, so a gallery or baseline run spawned
one browser per spec — a process-tree storm that drags the whole machine. This module owns the
**single** ``sync_playwright()`` instance for the process, launches the browser **lazily on first
raster**, and reuses it for every subsequent render.

Why a single instance is mandatory (not just an optimization): a second concurrent
``sync_playwright()`` in the same process raises *"Playwright Sync API inside the asyncio loop"*
(verified). So EVERY Chromium consumer — png, pdf, the ``doctor`` probe, the e2e test fixture, and
the dev tools — must go through this module; nothing else may open its own ``sync_playwright()``.

The sync API is also thread-bound: the instance belongs to the thread that created it. Access from
another thread raises a clear error (parallelism is multiprocessing, not threads).
"""
from __future__ import annotations

import atexit
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

    from playwright.sync_api import Browser, Page, Playwright

__all__ = ["chromium_executable", "raster_page", "shared_browser", "shutdown"]

_LOCK = threading.RLock()
_PW: Playwright | None = None  # the one started sync_playwright() for this process
_BROWSER: Browser | None = None  # launched lazily on first raster, reused thereafter
_OWNER_THREAD: int | None = None
_ATEXIT_REGISTERED = False


def _ensure_driver() -> Playwright:
    """Start the single persistent ``sync_playwright()`` (driver only — no browser launched)."""
    global _PW, _OWNER_THREAD, _ATEXIT_REGISTERED
    if _PW is None:
        from playwright.sync_api import sync_playwright

        _PW = sync_playwright().start()
        _OWNER_THREAD = threading.get_ident()
        if not _ATEXIT_REGISTERED:
            atexit.register(shutdown)
            _ATEXIT_REGISTERED = True
    return _PW


def _check_thread() -> None:
    if _OWNER_THREAD is not None and threading.get_ident() != _OWNER_THREAD:
        raise RuntimeError(
            "tarseem's Chromium pool is bound to the thread that first used it; the Playwright "
            "sync API cannot be driven from another thread. Render from one thread, or use "
            "separate processes for parallelism (each gets its own pool)."
        )


def _ensure_browser() -> Browser:
    """Return the shared browser, launching (or relaunching after a crash) as needed."""
    global _BROWSER
    pw = _ensure_driver()
    if _BROWSER is None or not _BROWSER.is_connected():
        _BROWSER = pw.chromium.launch()
    return _BROWSER


def chromium_executable() -> Path | None:
    """Path to the Playwright Chromium executable, or ``None`` if unavailable.

    Starts only the driver (no browser), so it is a cheap availability probe — used by ``doctor``
    and by test skip markers, replacing the old probes that cold-launched a browser at import time.
    """
    with _LOCK:
        try:
            exe = Path(_ensure_driver().chromium.executable_path)
        except Exception:  # noqa: BLE001 - any failure means Chromium is unavailable here
            return None
        return exe if exe.exists() else None


@contextmanager
def raster_page(**page_kwargs: object) -> Iterator[Page]:
    """Yield a fresh ``Page`` on the shared browser; close the page (and its owned context)
    afterwards while keeping the browser alive. A render error closes only the page, never the
    browser. Serialized by ``_LOCK`` (the sync API is single-threaded)."""
    with _LOCK:
        _check_thread()
        browser = _ensure_browser()
        page = browser.new_page(**page_kwargs)  # type: ignore[arg-type]
        try:
            yield page
        finally:
            try:
                page.close()
            except Exception:  # noqa: BLE001 - teardown best-effort; never mask the real error
                pass


def shared_browser() -> Browser:
    """The shared ``Browser`` for callers that manage their own pages (the e2e fixture, dev
    tools). Callers MUST close their own pages and MUST NOT close the browser (the pool owns it)."""
    with _LOCK:
        _check_thread()
        return _ensure_browser()


def shutdown() -> None:
    """Close the browser and stop the driver. Idempotent; registered at ``atexit`` and exposed as
    ``tarseem.shutdown()`` so an embedding host can release Chromium explicitly."""
    global _PW, _BROWSER, _OWNER_THREAD
    with _LOCK:
        if _BROWSER is not None:
            try:
                _BROWSER.close()
            except Exception:  # noqa: BLE001 - best-effort during shutdown
                pass
            _BROWSER = None
        if _PW is not None:
            try:
                _PW.stop()
            except Exception:  # noqa: BLE001 - best-effort during shutdown
                pass
            _PW = None
        _OWNER_THREAD = None
