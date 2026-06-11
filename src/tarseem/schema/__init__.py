"""Tarseem schema package: the core JSON Schema and loaders."""
from __future__ import annotations

from tarseem.schema.core import CORE_SCHEMA


def load_core_schema() -> dict:
    """Return the core diagram JSON Schema (2020-12)."""
    return CORE_SCHEMA


__all__ = ["CORE_SCHEMA", "load_core_schema"]
