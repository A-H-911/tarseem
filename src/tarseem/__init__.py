"""Tarseem — schema-driven diagram engine.

Public API (A4):

    from tarseem import Engine
    result = Engine().render(spec)
    result.export(["svg", "png"], "out/")
"""
from __future__ import annotations

__version__ = "0.0.0"

from tarseem.engine import Engine, RenderResult  # noqa: E402  (needs __version__ first)

__all__ = ["Engine", "RenderResult", "__version__"]
