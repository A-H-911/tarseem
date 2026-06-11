"""Docs verification (⚠3 / A9): the prose guide must stay true to the corpus.

Cheap guard against doc rot: every example referenced by the guide must exist, every
diagramType in the corpus must be documented, and every example file must be mentioned —
so a new family or a renamed example can't silently desync from the docs.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUIDE = ROOT / "docs" / "guide"
EXAMPLES = sorted((ROOT / "examples").glob("*.json"))


def _guide_text() -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in GUIDE.glob("*.md"))


def test_examples_referenced_in_guide_exist():
    text = _guide_text()
    for ref in set(re.findall(r"examples/([\w-]+\.json)", text)):
        assert (ROOT / "examples" / ref).exists(), f"guide references missing example: {ref}"


def test_every_example_is_documented():
    text = _guide_text()
    for ex in EXAMPLES:
        assert ex.name in text, f"example not mentioned in the guide: {ex.name}"


def test_every_diagram_type_is_documented():
    text = _guide_text()
    types = {json.loads(ex.read_text(encoding="utf-8"))["diagramType"] for ex in EXAMPLES}
    for t in types:
        assert t in text, f"diagramType not documented in the guide: {t}"


def test_quickstart_and_families_present():
    assert (GUIDE / "quickstart.md").exists()
    assert (GUIDE / "families.md").exists()
