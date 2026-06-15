# Exports

Tarseem lays out a diagram **once** into a positioned IR and then writes it through many
writers (ADR-001). The **SVG is the canonical artifact** — deterministic, font-embedded, and
RTL-first. Every other format is derived from that one source of truth, so what you see in the
SVG is what every export carries (within its medium).

| Format | Role | What it is |
|--------|------|-----------|
| **svg**   | publish · verify | The canonical vector artifact. Source of truth for all others. |
| **png**   | publish | A raster of the SVG via Chromium (ADR-003). |
| **pdf**   | publish · share | A single-page vector print of the SVG via Chromium. |
| **drawio**| refine | An editable [diagrams.net](https://www.drawio.com) file — native cells you can move/restyle. |
| **pptx**  | refine | An editable PowerPoint deck of **native** shapes/connectors (not an image). |

> Mermaid and PlantUML *source* exports (the "regenerate" role) are a deferred future feature —
> see [Deferred](#deferred-future-formats).

## Exporting

CLI — comma-separated formats, an output directory, and a basename:

```bash
tarseem export examples/swimlane-pipeline.json -f svg,png,pdf,drawio,pptx -o out/ -n pipeline
# svg: out/pipeline.svg
# png: out/pipeline.png
# ...
#   [pptx] capability report: 1 note(s)        # printed when an export is lossy
#     - fonts_embedded: PPTX names Cairo (a:cs); install Cairo to render it ...
```

Python:

```python
from tarseem import Engine

result = Engine().render(spec)
written = result.export(["svg", "png", "pdf", "drawio", "pptx"], "out/", name="pipeline")
for fmt, report in result.reports.items():
    if report.lossy:
        print(fmt, [w.message for w in report.warnings])
```

`render()` runs the full pipeline once; `export()` then writes each format from the shared IR.

## Capability reports — never a silent drop

Every writer-backed export (`png`, `pdf`, `drawio`, `pptx`) returns a **CapabilityReport**
(invariant 6): a per-feature `supports` map (`full` / `partial` / `none`) plus machine-readable
`warnings` for anything it cannot carry faithfully. The reports are collected on
`result.reports[<format>]`.

When an export is **lossy** (any axis below `full`, or any warning), a `<file>.report.json`
**sidecar** is written next to it so a downstream tool sees exactly what was traded away:

```jsonc
// out/arabic-flowchart.pdf.report.json
{
  "writer": "pdf",
  "supports": { "shapes": "full", "rtl_shaping": "full", "metadata": "full", ... },
  "warnings": [
    { "code": "text-layer-lossy", "feature": "rtl_shaping",
      "message": "RTL text is painted shaped ... copy/search of Arabic text is garbled",
      "element": null }
  ],
  "lossy": true
}
```

A clean export (e.g. a Latin PNG) is `lossy: false` and writes **no** sidecar.

The SVG carries no report: it is the reference every other format is measured against — it
cannot be lossy with respect to itself.

## Fidelity matrix

Support per feature, generated from the writers' own reports (not prose — see
`tarseem.report.FEATURES`). `full` = carried faithfully; `partial` = approximated or delegated to
the viewer; `none` = not representable.

| Feature | svg | png | pdf | drawio | pptx |
|---------|:---:|:---:|:---:|:------:|:----:|
| shapes | ◆ | full | full | full¹ | full¹ |
| lanes | ◆ | full | full | full² | full² |
| phases | ◆ | full | full | full² | full² |
| badges | ◆ | full | full | full | full |
| markers | ◆ | full | full | full | full |
| edge_routes | ◆ | full | full | full | full |
| edge_labels | ◆ | full | full | full | full |
| curved_edges | ◆ | full | full | **none** | **partial** |
| ports (ER rows) | ◆ | full | full | **partial**² | **partial**² |
| gradients | ◆ | full | full | **none** | **none** |
| fonts_embedded | ◆ | full | full | full | **none** |
| rtl_shaping | ◆ | full | full³ | **partial** | **partial** |
| theme_fidelity | ◆ | full | full | **partial** | **partial** |
| metadata | ◆ | full | full | full | full |

◆ = the canonical SVG defines the feature.
¹ An unknown shape falls back to a plain box + a warning.
² `lanes`/`phases`/`ports` report `none` when the diagram doesn't use them — a writer never claims
support for a feature that isn't present.
³ PDF paints Arabic correctly (shaped, joined, RTL) — `rtl_shaping` is `full` — but the
*extractable text layer* is not searchable for Arabic; a `text-layer-lossy` warning is attached
for RTL diagrams (the picture is right; copy/search is garbled). See [PDF](#pdf).

**png and pdf are faithful renders of the SVG, so every visual axis is `full`.** They differ from
the SVG only on the medium axes (`fonts_embedded`, `metadata`) and — for pdf — the searchable text
layer. The editable writers (drawio, pptx) reconstruct the IR with native shapes, so they trade
some fidelity for editability.

## Per-format notes

### SVG
The canonical artifact: deterministic (same spec + engine ⇒ byte-identical, A3), Cairo subset
embedded by default, per-label `direction="rtl"` for RTL. `render()` / `tarseem render` write it
with a provenance comment (spec hash + engine versions); `result.svg` is the byte-stable form
without it.

### PNG
A Chromium raster of the SVG — glyphs are baked to pixels, so it renders anywhere with no fonts
installed (`fonts_embedded: full`). Provenance travels in a `tEXt` chunk (`metadata: full`),
inserted without re-encoding the image, so the pixels are identical to a bare render. A faithful
raster has no lossy axes → no sidecar.

### PDF
A single-page vector print of the SVG via Chromium. Self-contained: the print backend (Skia)
carries glyph outlines as Type3 vector procedures, so it renders with zero fonts installed.
Provenance is embedded as a PDF Info dictionary via an append-only incremental update (no PDF
dependency; if it can't be applied safely the report honestly says `metadata: none`).

**Ceiling:** the *picture* is fully correct including shaped Arabic, but the extractable/searchable
**text layer is garbled for Arabic** (Type3 glyphs carry no reliable Unicode). Latin text copies
and searches fine. A searchable-Arabic layer was investigated and deferred (see spike-5).

### draw.io
Editable diagrams.net cells from the IR (ADR-007): lanes/phases are drawn as **explicit rects +
header chips** matching the SVG (including the RTL right-side flip), not native draggable
swimlanes; edges are exact polylines. The bundled Cairo subset is embedded into the file, so it
renders in Cairo with zero setup. Trades: orthogonal edges only (`curved_edges: none`), ER rows
folded into the entity label (`ports: partial`), bidi shaping delegated to diagrams.net's renderer
(`rtl_shaping: partial`). Lanes are static rects, flagged with an `editability-limited` warning.

### PPTX
Native PowerPoint shapes, connectors, and text from the IR — never an image or an SVG ungroup
(invariant 5). **Fonts are not embedded**: the deck *names* Cairo (including the complex-script
slot for Arabic), so **install Cairo** for correct rendering. See the
[PowerPoint workflow guide](powerpoint.md) for the open/edit/verify steps and the manual review
checklist.

## Determinism

Every writer is deterministic (invariant 7): the same spec + engine versions produce
byte-identical output. Wall-clock timestamps are stripped everywhere — PDF dates pinned, PPTX
core-property and zip timestamps pinned, font subsets codepoint-sorted — so artifacts never churn
on a re-run. Provenance carries only content-addressed, reproducible fields (spec hash, engine
versions, theme id).

## Deferred / future formats

- **Mermaid + PlantUML** source exports (best-effort, lossy, capability-reported) — deferred to a
  future feature.
- **Searchable Arabic in PDF** — investigated (spike-5), parked; the PDF stays visual-only for
  Arabic.
- **Zero-install font embedding in PPTX** — PowerPoint rejected a plain OPC embed; deferred.

See `docs/spikes/phase-6-progress.md` for the full deferred-task record.

## Next

- [PowerPoint workflow](powerpoint.md) — opening, editing, and verifying `.pptx` decks.
- [RTL & Arabic](rtl-arabic.md) — the end-to-end Arabic story (and the PDF text-layer caveat).
- [Diagram families](families.md) · [Quickstart](quickstart.md).
