"""A5 — Basic styling: theme + node/edge-level overrides + named presets functional.

Verification: unit (cascade) here; golden render verified with A2 (12-acceptance A5).
Cascade order (05 §2): theme -> theme.overrides -> group -> lane -> styleRefs -> inline.
"""
from __future__ import annotations

import copy

from tarseem.themes import DEFAULT_THEME
from tarseem.themes.cascade import resolve_edge_style, resolve_node_style


def _spec(node, **top):
    return {"specVersion": "0.1", "diagramType": "flowchart", "nodes": [node], **top}


def test_theme_default_applies():
    node = {"id": "n", "label": {"text": "x"}}
    assert resolve_node_style(_spec(node), node)["fill"] == DEFAULT_THEME["node"]["fill"]


def test_named_preset_applies_via_styleRefs():
    node = {"id": "n", "label": {"text": "x"}, "styleRefs": ["critical"]}
    spec = _spec(node, styles={"critical": {"fill": "#FDECEC"}})
    assert resolve_node_style(spec, node)["fill"] == "#FDECEC"


def test_inline_node_style_overrides_preset():
    node = {
        "id": "n", "label": {"text": "x"},
        "styleRefs": ["critical"], "style": {"fill": "#00FF00"},
    }
    spec = _spec(node, styles={"critical": {"fill": "#FDECEC"}})
    assert resolve_node_style(spec, node)["fill"] == "#00FF00"


def test_later_styleref_wins():
    node = {"id": "n", "label": {"text": "x"}, "styleRefs": ["a", "b"]}
    spec = _spec(node, styles={"a": {"fill": "#111111"}, "b": {"fill": "#222222"}})
    assert resolve_node_style(spec, node)["fill"] == "#222222"


def test_deep_merge_preserves_unset_subkeys():
    node = {"id": "n", "label": {"text": "x"}, "style": {"border": {"color": "#C0392B"}}}
    s = resolve_node_style(_spec(node), node)
    assert s["border"]["color"] == "#C0392B"
    assert s["border"]["width"] == DEFAULT_THEME["node"]["border"]["width"]


def test_lane_style_contributes_below_node():
    node = {"id": "n", "label": {"text": "x"}, "lane": "L"}
    spec = _spec(node, lanes=[{"id": "L", "style": {"fill": "#F4F8FB"}}])
    assert resolve_node_style(spec, node)["fill"] == "#F4F8FB"


def test_theme_overrides_dotted_keys_apply():
    node = {"id": "n", "label": {"text": "x"}}
    spec = _spec(node, theme={"overrides": {"node.fill": "#ABCDEF"}})
    assert resolve_node_style(spec, node)["fill"] == "#ABCDEF"


def test_edge_style_resolves():
    spec = {
        "specVersion": "0.1", "diagramType": "flowchart",
        "nodes": [{"id": "a", "label": {"text": "x"}}, {"id": "b", "label": {"text": "y"}}],
        "edges": [{"id": "e", "source": "a", "target": "b", "style": {"stroke": "#FF0000"}}],
    }
    assert resolve_edge_style(spec, spec["edges"][0])["stroke"] == "#FF0000"


def test_resolution_is_pure_and_does_not_share_theme_refs():
    node = {"id": "n", "label": {"text": "x"}, "style": {"fill": "#123456"}}
    spec = _spec(node)
    before = copy.deepcopy(spec)
    s = resolve_node_style(spec, node)
    s["border"]["width"] = 999  # mutating the result must not corrupt the theme
    assert spec == before
    assert DEFAULT_THEME["node"]["border"]["width"] != 999
