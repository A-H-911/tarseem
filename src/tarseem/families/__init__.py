"""Diagram-type registry (invariant 8): the one place families are discovered.

Every pipeline stage resolves a ``diagramType`` to a :class:`DiagramTypePlugin` via
:func:`get_plugin`; no stage hard-codes a family name. Discovery is **entry-point first**
(group ``tarseem.types``), so built-in and third-party families load through the identical
mechanism — the dogfood that proves the public plugin API (F9). Built-ins are also declared
as entry points in ``pyproject.toml``.

Robustness net: the bundled built-in modules under this package are *also* scanned and
``setdefault``-registered, so an editable checkout whose ``*.dist-info`` predates a new
entry-point declaration still has every built-in available. Entry-point plugins always win.
"""
from __future__ import annotations

import importlib
import pkgutil
from importlib import metadata as importlib_metadata

from tarseem.families.base import DiagramTypePlugin, Layouter, LayouterFactory, SvgRenderer

__all__ = [
    "DiagramTypePlugin",
    "Layouter",
    "LayouterFactory",
    "SvgRenderer",
    "get_plugin",
    "all_plugins",
    "register",
    "ENTRY_POINT_GROUP",
]

ENTRY_POINT_GROUP = "tarseem.types"

# Fallback used for any unregistered ``diagramType`` (a typo or an un-installed plugin):
# render it as a generic ELK graph rather than crashing — preserves the pre-registry behavior
# where an unknown type fell through to ELK layout + the generic renderer + ``rect`` defaults.
_DEFAULT_PLUGIN = DiagramTypePlugin(type_id="")

_registry: dict[str, DiagramTypePlugin] | None = None


def register(plugin: DiagramTypePlugin, into: dict[str, DiagramTypePlugin]) -> None:
    """Register ``plugin`` under its ``type_id`` (entry-point load wins over bundled scan)."""
    into[plugin.type_id] = plugin


def _load_entry_points(into: dict[str, DiagramTypePlugin]) -> None:
    for ep in importlib_metadata.entry_points(group=ENTRY_POINT_GROUP):
        plugin = ep.load()
        if isinstance(plugin, DiagramTypePlugin):
            register(plugin, into)


def _load_bundled(into: dict[str, DiagramTypePlugin]) -> None:
    """Scan this package's modules for a ``PLUGIN`` and ``setdefault`` it — the net that keeps
    built-ins available when entry-point metadata is stale. Entry-point loads (already present)
    are never overwritten."""
    for mod in pkgutil.iter_modules(__path__):
        if mod.name == "base":
            continue
        module = importlib.import_module(f"{__name__}.{mod.name}")
        plugin = getattr(module, "PLUGIN", None)
        if isinstance(plugin, DiagramTypePlugin):
            into.setdefault(plugin.type_id, plugin)


def _load() -> dict[str, DiagramTypePlugin]:
    registry: dict[str, DiagramTypePlugin] = {}
    _load_entry_points(registry)
    _load_bundled(registry)
    return registry


def get_plugin(type_id: str) -> DiagramTypePlugin:
    """Resolve a ``diagramType`` to its plugin, or the generic-ELK default for unknown types."""
    global _registry
    if _registry is None:
        _registry = _load()
    return _registry.get(type_id, _DEFAULT_PLUGIN)


def all_plugins() -> dict[str, DiagramTypePlugin]:
    """Every registered family, ``type_id -> plugin`` (a copy)."""
    global _registry
    if _registry is None:
        _registry = _load()
    return dict(_registry)
