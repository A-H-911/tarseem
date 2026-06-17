"""Tarseem — schema-driven diagram engine.

Public API (A4):

    from tarseem import Engine
    result = Engine().render(spec)
    result.export(["svg", "png"], "out/")
"""
from __future__ import annotations

__version__ = "0.0.0"

from tarseem.engine import Engine, RenderResult  # noqa: E402  (needs __version__ first)
from tarseem.render.browser import shutdown  # noqa: E402 - release the shared Chromium explicitly

__all__ = ["Engine", "RenderResult", "shutdown", "__version__"]
