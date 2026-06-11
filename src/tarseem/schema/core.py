"""Core JSON Schema (2020-12) for the Tarseem diagram spec (05 §1-3).

Small, stable universal vocabulary: meta/theme/direction/styles/lanes/phases/
nodes/groups/edges/layout/export. Profiles ($ref composition) extend this in
later phases; this is the pre-1.0 (0.x) core used by the MVP families.
"""
from __future__ import annotations

_LABEL = {
    "type": "object",
    "required": ["text"],
    "properties": {
        "text": {"type": "string"},
        "lang": {"type": "string"},
        "direction": {"enum": ["auto", "ltr", "rtl"]},
        "placement": {"type": "string"},
        "wrap": {"type": "boolean"},
        "maxWidth": {"type": "number"},
        "font": {"type": "object"},
    },
    "additionalProperties": True,
}

_PORT = {
    "type": "object",
    "required": ["id"],
    "properties": {
        "id": {"type": "string"},
        "side": {"enum": ["NORTH", "SOUTH", "EAST", "WEST"]},
        "offset": {"type": "number"},
    },
    "additionalProperties": False,
}

_NODE = {
    "type": "object",
    "required": ["id"],
    "properties": {
        "id": {"type": "string"},
        "kind": {"type": "string"},
        "shape": {"type": "string"},
        "lane": {"type": "string"},
        "phase": {"type": "string"},
        "label": _LABEL,
        "styleRefs": {"type": "array", "items": {"type": "string"}},
        "style": {"type": "object"},
        "size": {"type": "object"},
        "badge": {},
        "position": {"type": "object"},
        "ports": {"type": "array", "items": _PORT},
        "ext": {"type": "object"},
    },
    "patternProperties": {"^x-": {}},
    "additionalProperties": False,
}

_EDGE = {
    "type": "object",
    "required": ["source", "target"],
    "properties": {
        "id": {"type": "string"},
        "source": {"type": "string"},
        "target": {"type": "string"},
        "sourcePort": {"type": "string"},
        "targetPort": {"type": "string"},
        "label": _LABEL,
        "routing": {"type": "object"},
        "arrow": {"type": "object"},
        "style": {"type": "object"},
        "styleRefs": {"type": "array", "items": {"type": "string"}},
        "dashed": {"type": "boolean"},
    },
    "patternProperties": {"^x-": {}},
    "additionalProperties": False,
}

_LANE = {
    "type": "object",
    "required": ["id"],
    "properties": {
        "id": {"type": "string"},
        "label": _LABEL,
        "orientation": {"enum": ["horizontal", "vertical"]},
        "style": {"type": "object"},
        "hue": {"type": "string"},
        "order": {"type": "number"},
    },
    "additionalProperties": False,
}

_PHASE = {
    "type": "object",
    "required": ["id"],
    "properties": {
        "id": {"type": "string"},
        "label": _LABEL,
        "order": {"type": "number"},
    },
    "additionalProperties": False,
}

_GROUP = {
    "type": "object",
    "required": ["id"],
    "properties": {
        "id": {"type": "string"},
        "label": _LABEL,
        "children": {"type": "array", "items": {"type": "string"}},
        "collapsible": {"type": "boolean"},
        "style": {"type": "object"},
    },
    "additionalProperties": False,
}

CORE_SCHEMA: dict = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://tarseem.dev/schemas/diagram/0.x/core.json",
    "title": "Tarseem diagram core",
    "type": "object",
    "required": ["specVersion", "diagramType"],
    "properties": {
        "specVersion": {"type": "string", "pattern": r"^\d+\.\d+$"},
        "diagramType": {"type": "string"},
        "meta": {"type": "object"},
        "theme": {
            "type": "object",
            "properties": {"ref": {"type": "string"}, "overrides": {"type": "object"}},
            "additionalProperties": True,
        },
        "direction": {"enum": ["LR", "RL", "TB", "BT"]},
        "styles": {"type": "object", "additionalProperties": {"type": "object"}},
        "lanes": {"type": "array", "items": _LANE},
        "phases": {"type": "array", "items": _PHASE},
        "nodes": {"type": "array", "items": _NODE},
        "groups": {"type": "array", "items": _GROUP},
        "edges": {"type": "array", "items": _EDGE},
        "annotations": {"type": "array"},
        "layout": {"type": "object"},
        "export": {"type": "object"},
    },
    "patternProperties": {"^x-": {}},
    "additionalProperties": False,
}
