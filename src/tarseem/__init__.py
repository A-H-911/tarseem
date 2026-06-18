"""Tarseem — schema-driven diagram engine.

Public API (A4):

    from tarseem import Engine
    result = Engine().render(spec)
    result.export(["svg", "png"], "out/")

Agent surface (F11) — one call, JSON in / JSON out, never raises for a bad spec:

    from tarseem import generate, schema_bundle
    out = generate(spec)                 # {"ok": true, "svg": "...", "report": {...}}
    tools = schema_bundle()              # JSON Schema for IDE autocomplete / LLM tool-use
"""
from __future__ import annotations

__version__ = "1.0.0"

from tarseem.agent import generate  # noqa: E402 - agent surface (imports engine internally)
from tarseem.engine import Engine, RenderResult  # noqa: E402  (needs __version__ first)
from tarseem.render.browser import shutdown  # noqa: E402 - release the shared Chromium explicitly
from tarseem.schema import schema_bundle  # noqa: E402

__all__ = [
    "Engine",
    "RenderResult",
    "generate",
    "schema_bundle",
    "shutdown",
    "__version__",
]
