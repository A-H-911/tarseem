"""Gallery builder (A6/A9): renders the example corpus into a static HTML site.

One corpus, four consumers (09 §2): manual review, E2E, screenshot regression, docs. The
index thumbnails are the inline canonical SVG, so building the index needs no Chromium;
PNG is rendered best-effort as a download. A sample that fails to render is recorded with
its error and the build continues (invariant 6: capability reports, never silent drops).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from tarseem.engine import Engine
from tarseem.gallery.html import detail_body, index_card, page
from tarseem.report import RenderReport

__all__ = ["build_gallery", "GallerySample", "GalleryResult"]


@dataclass(frozen=True)
class GallerySample:
    name: str
    title: str
    family: str
    ok: bool
    report: RenderReport | None = None
    error: str | None = None


@dataclass(frozen=True)
class GalleryResult:
    out_dir: Path
    samples: tuple[GallerySample, ...]

    @property
    def index_path(self) -> Path:
        return self.out_dir / "index.html"


def _metrics_view(report: RenderReport) -> dict:
    d = report.to_dict()
    if d.get("render_ms") is not None:
        d["render_ms"] = round(d["render_ms"], 2)
    return d


def build_gallery(
    paths: list[Path], out_dir: Path, with_png: bool = True, node: str = "node"
) -> GalleryResult:
    """Render each spec in ``paths`` into ``out_dir`` as a static gallery. Returns a
    result recording per-sample success/failure. Paths are processed in sorted order so
    the index is deterministic regardless of filesystem ordering."""
    out_dir = Path(out_dir)
    samples_dir = out_dir / "samples"
    samples_dir.mkdir(parents=True, exist_ok=True)

    engine = Engine(node=node)
    samples: list[GallerySample] = []
    cards: list[str] = []

    # One ELK Node session reused across the whole corpus (instead of one spawn per spec).
    with engine:
        for path in sorted(paths, key=lambda p: p.stem):
            name = path.stem
            try:
                spec = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                samples.append(
                    GallerySample(name, name, "?", ok=False, error=f"unreadable spec: {exc}")
                )
                cards.append(index_card(name, name, "?", "", [], ok=False))
                continue

            family = str(spec.get("diagramType", "?"))
            title = str((spec.get("meta") or {}).get("title") or name)
            spec_json = json.dumps(spec, indent=2, ensure_ascii=False)

            try:
                res = engine.render(spec)
                svg = res.to_svg(provenance=True)
                report = res.report
            except Exception as exc:  # noqa: BLE001 - record any render failure, never drop it
                samples.append(GallerySample(name, title, family, ok=False, error=str(exc)))
                cards.append(index_card(name, title, family, "", [], ok=False))
                _write(out_dir / f"{name}.html", page(
                    title, detail_body(name, title, family, "", spec_json, {}, [], error=str(exc))))
                continue

            _write(samples_dir / f"{name}.svg", svg)
            downloads = [("SVG", f"samples/{name}.svg")]
            if with_png:
                try:
                    res.export(["png"], samples_dir, name)
                    downloads.append(("PNG", f"samples/{name}.png"))
                except Exception:  # noqa: BLE001 - PNG is best-effort (Chromium optional here)
                    pass

            metrics = _metrics_view(report)
            tags = [f"{metrics['node_count']} nodes", f"{metrics['crossings']} crossings"]
            cards.append(index_card(name, title, family, svg, tags, ok=True))
            _write(out_dir / f"{name}.html", page(
                title, detail_body(name, title, family, svg, spec_json, metrics, downloads, None)))
            samples.append(GallerySample(name, title, family, ok=True, report=report))

    _write(out_dir / "index.html", page("Tarseem Gallery", _index_html(cards)))
    return GalleryResult(out_dir=out_dir, samples=tuple(samples))


def _index_html(cards: list[str]) -> str:
    return (
        '<header class="masthead"><h1>Tarseem Gallery</h1>'
        "<p>Schema-driven diagrams rendered through one positioned IR. "
        "Every sample is a golden fixture for manual review, E2E, and screenshot regression."
        "</p></header>"
        f'<main class="wrap"><div class="grid">{"".join(cards)}</div></main>'
    )


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
