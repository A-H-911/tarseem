"""Export provenance metadata (08 §6), shared by every writer.

Every artifact embeds the same provenance fields so a diagram is traceable to the exact
spec + engine that produced it (NFR-1/6): generator, tarseem version, spec hash, spec
version, theme id, font set, layout engine + version.

Determinism note (invariant 7 / A3): the strategy doc lists a wall-clock ``timestamp`` in
§6, but byte-identical output forbids it — a timestamp would churn every golden on every
run. We deliberately OMIT the timestamp here; provenance carries only content-addressed,
reproducible fields. Same spec + same engine versions ⇒ byte-identical metadata.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tarseem.engine import RenderResult

__all__ = ["provenance", "as_comment", "as_text"]

_GENERATOR = "tarseem"


def provenance(result: RenderResult) -> dict[str, str]:
    """Ordered, deterministic provenance for a render. Values are all reproducible from the
    spec + pinned engine versions; no wall-clock, no environment-specific data."""
    diagram = result.diagram
    versions = result.versions
    layout_engine = "lanegrid" if diagram.lanes or diagram.orientation == "vertical" else "elk"
    if diagram.diagram_type == "sequence":
        layout_engine = "sequence"
    elif diagram.diagram_type in ("swimlane",):
        layout_engine = "lanegrid"
    elif "elkjs" in versions:
        layout_engine = "elk"
    meta: dict[str, str] = {
        "generator": _GENERATOR,
        "tarseemVersion": str(versions.get("tarseem", "")),
        "specHash": result.spec_hash,
        "diagramType": diagram.diagram_type,
        "layoutEngine": layout_engine,
    }
    if "elkjs" in versions:
        meta["elkjsVersion"] = str(versions["elkjs"])
    if "libavoid-js" in versions:
        meta["libavoidVersion"] = str(versions["libavoid-js"])
    theme_id = (diagram.theme or {}).get("id") or (diagram.theme or {}).get("ref")
    if theme_id:
        meta["theme"] = str(theme_id)
    return meta


def as_comment(meta: dict[str, str]) -> str:
    """Render provenance as a single XML comment line (drawio file comment, 08 §6). Sanitises
    the ``--`` sequence that would otherwise close a comment prematurely."""
    body = " ".join(f"{k}={v}" for k, v in meta.items())
    return f"<!-- {_GENERATOR} provenance: {body.replace('--', '- -')} -->"


def as_text(meta: dict[str, str]) -> str:
    """Render provenance as a compact ``k=v k=v`` line — the value of a PNG ``tEXt`` chunk
    (08 §6). Deterministic: the dict is already ordered and carries no wall-clock (invariant 7)."""
    return " ".join(f"{k}={v}" for k, v in meta.items())
