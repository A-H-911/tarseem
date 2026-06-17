"""Public diagram-type plugin contract (invariant 8, F9).

A diagram *type* ("family") is a plugin: a small declarative descriptor that tells each
pipeline stage how to treat a ``diagramType``. Built-ins and third-party types use the
**same** contract and the same ``tarseem.types`` entry-point registry (``families/__init__``);
nothing in the core pipeline hard-codes a family name — every stage looks the family up.

The descriptor is intentionally declarative (data, not subclassing): cloning an existing family
— the F9 benchmark, in well under a day — is a few lines:

    from tarseem.families.base import DiagramTypePlugin

    PLUGIN = DiagramTypePlugin(type_id="my-flow", default_shape="roundrect")
    # ELK layout + generic renderer inherited from the defaults; no core edits.

Fields a family may override (all optional except ``type_id``):

- ``default_shape``     node shape when a node omits ``shape`` (compile stage).
- ``member_compartments`` treat ``attributes``/``methods`` as UML compartments instead of
                        ER attribute rows (compile stage; only ``class`` sets this today).
- ``layouter_factory``  ``None`` ⇒ ELK (engine-managed, session-poolable). Otherwise a
                        zero-arg factory returning a one-shot layouter with
                        ``.layout(graph) -> PositionedDiagram`` (lane-grid, sequence, …).
- ``svg_renderer``      ``None`` ⇒ the generic graph renderer. Otherwise a callable
                        ``(PositionedDiagram) -> str`` (the dedicated er/class/sequence writer).
- ``export_chrome``     extra chrome the drawio/PPTX writers draw for this family
                        (``"sequence"`` ⇒ lifelines + activations). Swimlane band chrome is
                        keyed structurally off ``diagram.lanes``, not here.
- ``layout_engine_name`` provenance label for the layout stage (08 §6 metadata).
- ``schema_extension``  optional JSON-Schema fragment a profile adds on top of the core
                        (05 §1 ``$ref`` composition). Reserved for typed profiles; the core
                        already accepts any registered ``diagramType`` string.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from tarseem.model.ir import LogicalGraph, PositionedDiagram


class Layouter(Protocol):
    """A one-shot, stateless layouter (lane-grid, sequence). ELK families use ``None`` and
    the engine's pooled subprocess path instead."""

    def layout(self, graph: LogicalGraph) -> PositionedDiagram: ...


LayouterFactory = Callable[[], "Layouter"]
SvgRenderer = Callable[["PositionedDiagram"], str]


@dataclass(frozen=True)
class DiagramTypePlugin:
    """Declarative descriptor for one diagram family. Immutable (coding-style: immutability)."""

    type_id: str
    default_shape: str = "rect"
    member_compartments: bool = False
    layouter_factory: LayouterFactory | None = None
    svg_renderer: SvgRenderer | None = None
    export_chrome: str | None = None
    layout_engine_name: str = "elk"
    schema_extension: dict | None = None
