"""Engine facade (A4): the clean public API.

    from tarseem import Engine
    result = Engine().render(spec)
    result.export(["svg", "png"], "out/")

Orchestrates the pipeline (validate -> compile -> measure -> layout -> writers) and
dispatches the layouter by family: swimlanes use the pure-Python lane-grid layouter,
graph families (flowchart/architecture/dependency) use ELK. Invalid specs raise
``SpecValidationError`` with the same coded, path-precise issues as ``validate`` (A1).
Artifacts can embed a content-addressed spec hash + engine versions (invariant 7).
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from tarseem import __version__
from tarseem.layout.elk import ElkLayout
from tarseem.layout.lanegrid import LaneGridLayout
from tarseem.layout.sequence import SequenceLayout
from tarseem.measure import measure_graph
from tarseem.model import PositionedDiagram, compile_spec
from tarseem.render import render_svg
from tarseem.validation import validate

if TYPE_CHECKING:
    from tarseem.report import RenderReport

__all__ = ["Engine", "RenderResult"]

_SWIMLANE_TYPES = {"swimlane"}
_SEQUENCE_TYPES = {"sequence"}


def spec_hash(spec: dict) -> str:
    """Content-addressed hash of a spec (stable across key order / re-serialization)."""
    canonical = json.dumps(spec, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass
class RenderResult:
    """A laid-out diagram plus its provenance; renders/exports on demand."""

    diagram: PositionedDiagram
    spec_hash: str
    versions: dict = field(default_factory=dict)
    layout_ms: float | None = None
    export_opts: dict = field(default_factory=dict)  # resolved spec.export.svg options
    _svg: str | None = field(default=None, repr=False)

    @property
    def report(self) -> RenderReport:
        """Quality metrics (crossings/overlaps/extent) + layout timing for this render."""
        from tarseem.report import analyze

        return analyze(self.diagram, render_ms=self.layout_ms)

    @property
    def svg(self) -> str:
        """Canonical SVG (no provenance comment — byte-stable, see A3). Applies the
        resolved ``export.svg`` options (embedFonts / textAsPaths); defaults are a no-op."""
        if self._svg is None:
            from tarseem.render.export_opts import apply_export_options

            self._svg = apply_export_options(render_svg(self.diagram), self.export_opts)
        return self._svg

    def to_svg(self, provenance: bool = False) -> str:
        if not provenance:
            return self.svg
        meta = (
            f"<!-- tarseem {self.versions.get('tarseem', __version__)} "
            f"spec-hash={self.spec_hash} "
            f"elkjs={self.versions.get('elkjs', 'n/a')} -->"
        )
        head, _, rest = self.svg.partition(">")
        return f"{head}>\n{meta}{rest}" if rest else self.svg

    def export(
        self, formats: list[str], out_dir: str | Path = ".", name: str = "diagram"
    ) -> dict[str, Path]:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        written: dict[str, Path] = {}
        svg_text = self.to_svg(provenance=True)
        for fmt in formats:
            if fmt == "svg":
                path = out / f"{name}.svg"
                path.write_text(svg_text, encoding="utf-8")
                written["svg"] = path
            elif fmt == "png":
                from tarseem.export import svg_to_png

                written["png"] = svg_to_png(svg_text, out / f"{name}.png")
            else:
                raise ValueError(f"unsupported export format: {fmt!r} (have: svg, png)")
        return written


class Engine:
    """Public entry point. Stateless; safe to construct per render or reuse."""

    def __init__(self, node: str = "node") -> None:
        self._node = node

    def render(self, spec: dict) -> RenderResult:
        result = validate(spec)
        if not result.ok:
            from tarseem.errors import SpecValidationError

            raise SpecValidationError(result)

        graph = measure_graph(compile_spec(spec))
        versions = {"tarseem": __version__}
        start = time.perf_counter()
        if graph.diagram_type in _SWIMLANE_TYPES:
            diagram = LaneGridLayout().layout(graph)
        elif graph.diagram_type in _SEQUENCE_TYPES:
            diagram = SequenceLayout().layout(graph)
        else:
            with ElkLayout(node=self._node) as elk:
                diagram = elk.layout(graph)
                versions["elkjs"] = elk.capabilities()["elkjs_version"]
        layout_ms = (time.perf_counter() - start) * 1000.0
        return RenderResult(
            diagram=diagram,
            spec_hash=spec_hash(spec),
            versions=versions,
            layout_ms=layout_ms,
            export_opts=(spec.get("export") or {}).get("svg") or {},
        )
