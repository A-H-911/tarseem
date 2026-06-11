"""Style cascade resolution (FR-5.2, A5).

Resolves a backend-neutral style dict for a node or edge by deep-merging layers
in precedence order (later wins):

    theme base -> theme.overrides -> group -> lane -> styleRefs (in order) -> inline style

Resolution happens here in the engine so writers receive already-resolved styles
(FR-5.4). Pure: never mutates the spec or the theme.
"""
from __future__ import annotations

import copy

from tarseem.themes import DEFAULT_THEME


def _normalize(style: dict | None) -> dict:
    """Expand dotted keys (``node.fill`` / ``border.color``) into nested dicts."""
    out: dict = {}
    for key, value in (style or {}).items():
        target = out
        parts = key.split(".")
        for part in parts[:-1]:
            nxt = target.get(part)
            if not isinstance(nxt, dict):
                nxt = {}
                target[part] = nxt
            target = nxt
        leaf = parts[-1]
        target[leaf] = _normalize(value) if isinstance(value, dict) else value
    return out


def _deep_merge(base: dict, over: dict) -> dict:
    result = copy.deepcopy(base)
    for key, value in over.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _overrides_for(spec: dict, kind: str) -> dict:
    overrides = _normalize((spec.get("theme") or {}).get("overrides") or {})
    target = overrides.get(kind)
    return target if isinstance(target, dict) else {}


def _resolve(layers: list[dict]) -> dict:
    result: dict = {}
    for layer in layers:
        result = _deep_merge(result, layer)
    return result


def resolve_node_style(spec: dict, node: dict, theme: dict | None = None) -> dict:
    theme = theme or DEFAULT_THEME
    styles = spec.get("styles") or {}
    layers: list[dict] = [theme["node"], _overrides_for(spec, "node")]

    node_id = node.get("id")
    for group in spec.get("groups") or []:
        if node_id in (group.get("children") or []):
            layers.append(_normalize(group.get("style")))

    lane_id = node.get("lane")
    if lane_id:
        for lane in spec.get("lanes") or []:
            if lane.get("id") == lane_id:
                layers.append(_normalize(lane.get("style")))

    for ref in node.get("styleRefs") or []:
        layers.append(_normalize(styles.get(ref)))
    layers.append(_normalize(node.get("style")))
    return _resolve(layers)


def resolve_edge_style(spec: dict, edge: dict, theme: dict | None = None) -> dict:
    theme = theme or DEFAULT_THEME
    styles = spec.get("styles") or {}
    layers: list[dict] = [theme["edge"], _overrides_for(spec, "edge")]
    for ref in edge.get("styleRefs") or []:
        layers.append(_normalize(styles.get(ref)))
    layers.append(_normalize(edge.get("style")))
    return _resolve(layers)


__all__ = ["resolve_node_style", "resolve_edge_style"]
