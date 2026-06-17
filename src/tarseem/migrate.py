"""Spec migration to the current schema MAJOR (v1.0 freeze, ADR-009).

The engine reads only the current MAJOR (1.x). ``migrate_spec`` upgrades an older spec in place
of a manual edit: it is pure (returns a new dict, never mutates the input) and idempotent.

v1.0 transforms:
- ``specVersion`` -> ``"1.0"`` (0.x is no longer accepted by the validator);
- drop the unused node ``kind`` field (removed from the schema at v1.0).
"""
from __future__ import annotations

import copy

CURRENT_VERSION = "1.0"

__all__ = ["migrate_spec", "CURRENT_VERSION"]


def migrate_spec(spec: dict) -> dict:
    """Return a copy of ``spec`` upgraded to the current schema version."""
    out = copy.deepcopy(spec)
    out["specVersion"] = CURRENT_VERSION
    for node in out.get("nodes", []) or []:
        if isinstance(node, dict):
            node.pop("kind", None)  # removed at v1.0 (was never read)
    return out
