"""Validation pipeline (05 §4): structural -> referential -> semantic.

``validate`` is pure: it never mutates the input spec and returns a structured
``ValidationResult`` of coded, path-precise issues. Capability checking (layer 4)
is added when adapters are wired (ADR-005).
"""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from jsonschema import Draft202012Validator

from tarseem.errors import Issue, ValidationResult
from tarseem.schema import CORE_SCHEMA

_VALIDATOR = Draft202012Validator(CORE_SCHEMA)


def _ptr(parts: Iterable[Any]) -> str:
    parts = list(parts)
    return "/" + "/".join(str(p) for p in parts) if parts else "/"


def _schema_hint(err: Any) -> str:
    v = err.validator
    if v == "required":
        return "add the missing required property"
    if v == "type":
        return f"expected type: {err.validator_value}"
    if v == "enum":
        return f"allowed values: {err.validator_value}"
    if v == "additionalProperties":
        return "unknown property (typo? or use an x-* vendor key)"
    if v == "pattern":
        return "value does not match the required format"
    return "see the core schema for the expected shape"


def _check_dup(items: list, key: str, id_map: dict, errors: list[Issue]) -> None:
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        iid = item.get("id")
        if iid is None:
            continue
        if iid in id_map:
            errors.append(
                Issue(
                    "E_DUP_ID",
                    f"/{key}/{i}/id",
                    f"duplicate id '{iid}' (first seen at /{key}/{id_map[iid]}/id)",
                    hint="ids must be unique within their collection",
                )
            )
        else:
            id_map[iid] = i


def validate(spec: dict) -> ValidationResult:
    """Validate a diagram spec. Returns coded errors + non-fatal warnings."""
    errors: list[Issue] = []
    warnings: list[Issue] = []

    # Layer 1 - structural (JSON Schema)
    structural = sorted(_VALIDATOR.iter_errors(spec), key=lambda e: list(e.absolute_path))
    for e in structural:
        errors.append(Issue("E_SCHEMA", _ptr(e.absolute_path), e.message, hint=_schema_hint(e)))
    if structural:
        # shape is unreliable; do not run referential checks on it
        return ValidationResult(errors=errors, warnings=warnings)

    nodes = spec.get("nodes", []) or []
    edges = spec.get("edges", []) or []
    lanes = spec.get("lanes", []) or []
    phases = spec.get("phases", []) or []
    groups = spec.get("groups", []) or []
    styles = spec.get("styles", {}) or {}

    # Layer 2 - referential
    node_ids: dict = {}
    lane_ids: dict = {}
    phase_ids: dict = {}
    group_ids: dict = {}
    _check_dup(nodes, "nodes", node_ids, errors)
    _check_dup(lanes, "lanes", lane_ids, errors)
    _check_dup(phases, "phases", phase_ids, errors)
    _check_dup(edges, "edges", {}, errors)
    _check_dup(groups, "groups", group_ids, errors)

    node_ports: dict[str, set] = {}
    for i, n in enumerate(nodes):
        # an edge may anchor to an explicit ELK port OR an ER attribute row (family: er)
        node_ports[n.get("id")] = {p.get("id") for p in (n.get("ports") or [])} | {
            a.get("id") for a in (n.get("attributes") or [])
        }
        lane = n.get("lane")
        if lane is not None and lane not in lane_ids:
            errors.append(
                Issue("E_BAD_LANE", f"/nodes/{i}/lane", f"node references unknown lane '{lane}'",
                      hint="declare the lane under spec.lanes or fix the id")
            )
        phase = n.get("phase")
        if phase is not None and phase not in phase_ids:
            errors.append(Issue(
                "E_BAD_PHASE", f"/nodes/{i}/phase",
                f"node references unknown phase '{phase}'",
                hint="declare the phase under spec.phases",
            ))
        for sref in n.get("styleRefs") or []:
            if sref not in styles:
                errors.append(Issue(
                    "E_BAD_STYLEREF", f"/nodes/{i}/styleRefs",
                    f"unknown style preset '{sref}'",
                    hint="define it under spec.styles",
                ))

    endpoint_ids = set(node_ids) | set(group_ids)
    for i, e in enumerate(edges):
        src, tgt = e.get("source"), e.get("target")
        if src not in endpoint_ids:
            errors.append(Issue(
                "E_BAD_REF", f"/edges/{i}/source",
                f"edge source '{src}' is not a node/group id",
                hint="point at an existing node id",
            ))
        if tgt not in endpoint_ids:
            errors.append(Issue(
                "E_BAD_REF", f"/edges/{i}/target",
                f"edge target '{tgt}' is not a node/group id",
                hint="point at an existing node id",
            ))
        sp = e.get("sourcePort")
        if sp is not None and sp not in node_ports.get(src, set()):
            errors.append(Issue("E_BAD_PORT", f"/edges/{i}/sourcePort",
                                f"unknown port '{sp}' on node '{src}'",
                                hint="declare the port under that node.ports"))
        tp = e.get("targetPort")
        if tp is not None and tp not in node_ports.get(tgt, set()):
            errors.append(Issue("E_BAD_PORT", f"/edges/{i}/targetPort",
                                f"unknown port '{tp}' on node '{tgt}'",
                                hint="declare the port under that node.ports"))
        for sref in e.get("styleRefs") or []:
            if sref not in styles:
                errors.append(Issue("E_BAD_STYLEREF", f"/edges/{i}/styleRefs",
                                    f"unknown style preset '{sref}'",
                                    hint="define it under spec.styles"))

    for i, g in enumerate(groups):
        for j, child in enumerate(g.get("children") or []):
            if child not in node_ids and child not in group_ids:
                errors.append(Issue("E_BAD_REF", f"/groups/{i}/children/{j}",
                                    f"group child '{child}' is not a node/group id",
                                    hint="reference an existing node id"))

    # Layer 3 - semantic warnings (only meaningful once references resolve)
    if not errors and len(nodes) > 1:
        referenced: set = set()
        for e in edges:
            referenced.add(e.get("source"))
            referenced.add(e.get("target"))
        for i, n in enumerate(nodes):
            if n.get("id") not in referenced:
                warnings.append(Issue("W_ORPHAN", f"/nodes/{i}",
                                      f"node '{n.get('id')}' has no edges",
                                      hint="connect it or remove it", severity="warning"))

    return ValidationResult(errors=errors, warnings=warnings)


__all__ = ["validate"]
