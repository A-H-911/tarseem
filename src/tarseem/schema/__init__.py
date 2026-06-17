"""Tarseem schema package: the core JSON Schema and loaders."""
from __future__ import annotations

import copy

from tarseem.schema.core import CORE_SCHEMA


def load_core_schema() -> dict:
    """Return the core diagram JSON Schema (2020-12), as used internally for validation."""
    return CORE_SCHEMA


def schema_bundle() -> dict:
    """A self-contained JSON-Schema bundle for IDE ``$schema`` autocomplete and LLM tool-use
    (05 §5). It is the core schema with ``diagramType`` enriched by the **currently registered**
    families (built-ins + any installed plugin), so a tool sees exactly which types are valid.

    Generated from the live registry, not hand-maintained — the validation schema itself stays
    permissive (any registered ``diagramType`` string), so this is a publishing view, not a
    stricter validator.
    """
    from tarseem.families import all_plugins

    bundle = copy.deepcopy(CORE_SCHEMA)
    types = sorted(all_plugins())
    bundle["properties"]["diagramType"] = {
        "type": "string",
        "description": "Registered diagram family (built-ins + installed plugins).",
        "enum": types,
    }
    return bundle


__all__ = ["CORE_SCHEMA", "load_core_schema", "schema_bundle"]
