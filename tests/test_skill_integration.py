"""Phase 7 / F11 — reference slash-command/skill integration example.

The skill at ``integrations/claude-skill/SKILL.md`` instructs an agent to drive the agent
surface (``tarseem schema`` / ``tarseem generate``) and self-repair against the JSON error
contract. These tests keep that documentation honest against the real CLI, and exercise the
exact flow the skill prescribes end to end.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from tarseem.cli import SUBCOMMANDS, main

SKILL = Path("integrations/claude-skill/SKILL.md")


def _frontmatter(text: str) -> dict:
    assert text.startswith("---"), "SKILL.md must open with YAML frontmatter"
    block = text.split("---", 2)[1]
    fields: dict[str, str] = {}
    for line in block.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            fields[key.strip()] = val.strip()
    return fields


def test_skill_has_name_and_description_frontmatter():
    fm = _frontmatter(SKILL.read_text(encoding="utf-8"))
    assert fm.get("name") == "tarseem-diagram"
    assert len(fm.get("description", "")) > 40  # a real trigger description, not a stub


def test_skill_only_references_real_cli_commands():
    """Rot guard: every `tarseem <sub>` the skill mentions must be a real subcommand."""
    text = SKILL.read_text(encoding="utf-8")
    referenced = set(re.findall(r"tarseem ([a-z]+)", text))
    assert referenced, "skill should reference the tarseem CLI"
    unknown = referenced - set(SUBCOMMANDS)
    assert unknown == set(), f"skill references non-existent CLI commands: {unknown}"
    assert {"schema", "generate"} <= referenced  # the surface the skill is built on


def test_skill_prescribed_flow_renders_an_artifact(tmp_path, capsys):
    """Run the skill's exact steps via the real CLI: discover schema -> author -> generate."""
    assert main(["schema"]) == 0
    bundle = json.loads(capsys.readouterr().out)
    assert "swimlane" in bundle["properties"]["diagramType"]["enum"]

    spec = tmp_path / "s.json"
    spec.write_text(json.dumps({
        "specVersion": "1.0",
        "diagramType": "swimlane",
        "lanes": [{"id": "s", "label": {"text": "Sales"}},
                  {"id": "w", "label": {"text": "Warehouse"}}],
        "nodes": [{"id": "n1", "lane": "s", "label": {"text": "Place order"}},
                  {"id": "n2", "lane": "w", "label": {"text": "Ship"}}],
        "edges": [{"id": "e1", "source": "n1", "target": "n2"}],
    }), encoding="utf-8")

    assert main(["generate", str(spec), "-f", "svg", "-o", str(tmp_path), "-n", "flow"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert (tmp_path / "flow.svg").exists()


def test_skill_self_repair_loop_uses_path_and_hint():
    """The documented loop: an invalid spec yields a coded error with a JSON-Pointer path and a
    hint; applying it and re-running succeeds — with no exception in between."""
    from tarseem import generate

    broken = {"diagramType": "swimlane",
              "lanes": [{"id": "s", "label": {"text": "Sales"}}],
              "nodes": [], "edges": []}  # missing required specVersion
    first = generate(broken)
    assert first["ok"] is False
    err = first["errors"][0]
    assert err["path"].startswith("/") and err["hint"]  # actionable for an agent

    fixed = {**broken, "specVersion": "1.0",
             "nodes": [{"id": "n1", "lane": "s", "label": {"text": "Place order"}}]}
    second = generate(fixed)
    assert second["ok"] is True
    assert second["svg"].lstrip().startswith("<svg")
