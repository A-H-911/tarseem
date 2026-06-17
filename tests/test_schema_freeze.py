"""Phase 7 / F12 — schema v1.0 freeze: version gate, profile enforcement, migration (ADR-009).

Decisions (2026-06-17): ratify the as-built schema as 1.0; require 1.x (reject 0.x); drop the
dead node ``kind``; enforce per-family profiles via plugin ``schema_extension``.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tarseem import schema_bundle
from tarseem.cli import main
from tarseem.migrate import CURRENT_VERSION, migrate_spec
from tarseem.validation import validate


def _spec(**over) -> dict:
    base = {"specVersion": "1.0", "diagramType": "flowchart",
            "nodes": [{"id": "n", "label": {"text": "x"}}], "edges": []}
    base.update(over)
    return base


# ---- the freeze is ratify-as-built: every shipped example still validates ----
@pytest.mark.parametrize("path", sorted(str(p) for p in Path("examples").glob("*.json")))
def test_every_example_validates_at_v1(path):
    result = validate(json.loads(Path(path).read_text(encoding="utf-8")))
    assert result.ok, [e.to_dict() for e in result.errors]


# ---- version gate: require 1.x, reject 0.x with a migrate hint --------------
def test_pre_1_0_spec_is_rejected_with_migrate_hint():
    result = validate(_spec(specVersion="0.1"))
    assert not result.ok
    err = result.errors[0]
    assert err.code == "E_VERSION"
    assert err.path == "/specVersion"
    assert "migrate" in err.hint


def test_v1_spec_is_accepted():
    assert validate(_spec()).ok


# ---- dropped node `kind` ----------------------------------------------------
def test_node_kind_is_no_longer_allowed():
    result = validate(_spec(nodes=[{"id": "n", "kind": "process", "label": {"text": "x"}}]))
    assert not result.ok
    assert result.errors[0].code == "E_SCHEMA"  # additionalProperties: kind removed at v1.0


# ---- per-family profiles (anti-generic guard) -------------------------------
def test_swimlane_requires_lanes():
    bad = {"specVersion": "1.0", "diagramType": "swimlane", "nodes": [], "edges": []}
    result = validate(bad)
    assert not result.ok
    assert any(e.code == "E_PROFILE" for e in result.errors)


def test_sequence_forbids_lanes():
    bad = {"specVersion": "1.0", "diagramType": "sequence",
           "lanes": [{"id": "a", "label": {"text": "A"}}], "nodes": [], "edges": []}
    result = validate(bad)
    assert not result.ok
    assert any(e.code == "E_PROFILE" and e.path == "/lanes" for e in result.errors)


def test_valid_family_specs_pass_their_profile():
    swim = {"specVersion": "1.0", "diagramType": "swimlane",
            "lanes": [{"id": "a", "label": {"text": "A"}}],
            "nodes": [{"id": "n", "lane": "a", "label": {"text": "x"}}], "edges": []}
    seq = {"specVersion": "1.0", "diagramType": "sequence",
           "nodes": [{"id": "n", "label": {"text": "x"}}], "edges": []}
    assert validate(swim).ok
    assert validate(seq).ok


# ---- migration --------------------------------------------------------------
def test_migrate_bumps_version_and_strips_kind():
    out = migrate_spec({"specVersion": "0.1", "diagramType": "flowchart",
                        "nodes": [{"id": "n", "kind": "process", "label": {"text": "x"}}],
                        "edges": []})
    assert out["specVersion"] == CURRENT_VERSION == "1.0"
    assert "kind" not in out["nodes"][0]


def test_migrate_is_pure_and_idempotent():
    src = {"specVersion": "0.1", "diagramType": "flowchart", "nodes": [], "edges": []}
    once = migrate_spec(src)
    assert src["specVersion"] == "0.1"  # input untouched
    assert migrate_spec(once) == once  # idempotent


def test_migrated_spec_validates():
    migrated = migrate_spec({"specVersion": "0.1", "diagramType": "flowchart",
                             "nodes": [{"id": "n", "kind": "x", "label": {"text": "x"}}],
                             "edges": []})
    assert validate(migrated).ok


# ---- the frozen bundle ------------------------------------------------------
def test_schema_bundle_is_frozen_at_v1():
    bundle = schema_bundle()
    assert bundle["$id"].endswith("/1.0/core.json")
    assert bundle["properties"]["specVersion"]["pattern"] == r"^1\.\d+$"


# ---- CLI migrate ------------------------------------------------------------
def test_cli_migrate_writes_a_valid_v1_spec(tmp_path):
    old = tmp_path / "old.json"
    old.write_text(json.dumps({"specVersion": "0.1", "diagramType": "flowchart",
                               "nodes": [{"id": "n", "label": {"text": "x"}}], "edges": []}),
                   encoding="utf-8")
    out = tmp_path / "new.json"
    assert main(["migrate", str(old), "-o", str(out)]) == 0
    migrated = json.loads(out.read_text(encoding="utf-8"))
    assert migrated["specVersion"] == "1.0"
    assert validate(migrated).ok
