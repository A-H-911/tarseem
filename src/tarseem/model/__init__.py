"""Diagram IR + spec compiler (ADR-001: one positioned IR, many writers)."""
from __future__ import annotations

from tarseem.model.compile import compile_spec
from tarseem.model.ir import (
    Activation,
    Label,
    LaneBand,
    LogicalEdge,
    LogicalGraph,
    LogicalLane,
    LogicalNode,
    LogicalPhase,
    Marker,
    PhaseBand,
    PositionedDiagram,
    PositionedEdge,
    PositionedNode,
)

__all__ = [
    "compile_spec",
    "Label",
    "LogicalLane",
    "LogicalPhase",
    "LogicalNode",
    "LogicalEdge",
    "LogicalGraph",
    "LaneBand",
    "PhaseBand",
    "Marker",
    "Activation",
    "PositionedNode",
    "PositionedEdge",
    "PositionedDiagram",
]
