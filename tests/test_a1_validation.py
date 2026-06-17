"""A1 — Validated JSON specs accepted; invalid specs rejected with path-precise coded errors.

Verification: schema test corpus (12-acceptance-criteria.md A1).
"""
from __future__ import annotations

import copy

from tarseem.validation import validate


def minimal_flowchart() -> dict:
    return {
        "specVersion": "1.0",
        "diagramType": "flowchart",
        "nodes": [
            {"id": "a", "label": {"text": "Start"}},
            {"id": "b", "label": {"text": "End"}},
        ],
        "edges": [{"id": "e1", "source": "a", "target": "b"}],
    }


# ---- acceptance ----
def test_minimal_valid_spec_accepted():
    result = validate(minimal_flowchart())
    assert result.ok
    assert result.errors == []


def test_five_line_spec_renders_decently_is_valid():
    # defaults philosophy (05 §5): a tiny spec must validate
    spec = {
        "specVersion": "1.0",
        "diagramType": "flowchart",
        "nodes": [{"id": "n1", "label": {"text": "Hi"}}],
    }
    assert validate(spec).ok


# ---- structural rejection ----
def test_missing_specversion_rejected_with_path():
    spec = minimal_flowchart()
    del spec["specVersion"]
    result = validate(spec)
    assert not result.ok
    codes = {e.code for e in result.errors}
    assert "E_SCHEMA" in codes
    # path points at the offending location (root for a missing required key)
    assert any(e.path in ("/", "") for e in result.errors)


def test_wrong_type_rejected():
    spec = minimal_flowchart()
    spec["nodes"] = "not-an-array"
    result = validate(spec)
    assert not result.ok
    assert any(e.code == "E_SCHEMA" and e.path == "/nodes" for e in result.errors)


def test_label_must_be_object_not_bare_string():
    spec = minimal_flowchart()
    spec["nodes"][0]["label"] = "bare string"
    result = validate(spec)
    assert not result.ok
    assert any(e.path == "/nodes/0/label" for e in result.errors)


# ---- referential rejection ----
def test_duplicate_node_id_rejected():
    spec = minimal_flowchart()
    spec["nodes"][1]["id"] = "a"
    result = validate(spec)
    assert not result.ok
    assert any(e.code == "E_DUP_ID" for e in result.errors)


def test_dangling_edge_endpoint_rejected_with_path():
    spec = minimal_flowchart()
    spec["edges"][0]["target"] = "missing"
    result = validate(spec)
    assert not result.ok
    assert any(e.code == "E_BAD_REF" and e.path == "/edges/0/target" for e in result.errors)


def test_unknown_lane_ref_rejected():
    spec = minimal_flowchart()
    spec["nodes"][0]["lane"] = "ghost"
    result = validate(spec)
    assert not result.ok
    assert any(e.code == "E_BAD_LANE" and e.path == "/nodes/0/lane" for e in result.errors)


def test_unknown_styleref_rejected():
    spec = minimal_flowchart()
    spec["nodes"][0]["styleRefs"] = ["nope"]
    result = validate(spec)
    assert not result.ok
    assert any(e.code == "E_BAD_STYLEREF" for e in result.errors)


def test_unknown_port_ref_rejected():
    spec = minimal_flowchart()
    spec["nodes"][0]["ports"] = [{"id": "out", "side": "EAST"}]
    spec["edges"][0]["sourcePort"] = "ghost"
    result = validate(spec)
    assert not result.ok
    assert any(e.code == "E_BAD_PORT" for e in result.errors)


# ---- semantic warnings (non-fatal) ----
def test_orphan_node_is_warning_not_error():
    spec = minimal_flowchart()
    spec["nodes"].append({"id": "c", "label": {"text": "Lonely"}})
    result = validate(spec)
    assert result.ok  # warnings do not fail validation
    assert any(w.code == "W_ORPHAN" for w in result.warnings)


# ---- error object contract (05 §5) ----
def test_error_objects_are_machine_actionable():
    spec = minimal_flowchart()
    spec["edges"][0]["target"] = "missing"
    err = validate(spec).errors[0]
    assert err.code and isinstance(err.code, str)
    assert err.path.startswith("/")
    assert err.message
    assert hasattr(err, "hint")
    d = err.to_dict()
    assert set(d) >= {"code", "path", "message", "hint"}


def test_validation_is_pure_does_not_mutate_input():
    spec = minimal_flowchart()
    before = copy.deepcopy(spec)
    validate(spec)
    assert spec == before
