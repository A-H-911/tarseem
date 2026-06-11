# Rendering, Export & Editable-Output Strategy

Status: Proposed · 2026-06-11
Core property: one positioned IR → many writers (see `04-architecture.md` §1). Four output roles per the brief: **publish** (static) / **refine** (editable) / **regenerate** (source) / **verify** (browser).

---

## 1. Format Tiers

| Tier | Formats | Role | Mechanism |
|---|---|---|---|
| **First-class** (CI-gated, full fidelity) | SVG · PNG · HTML gallery · JSON spec (authoritative source) | publish / verify / regenerate | Own SVG renderer; Playwright PNG; gallery builder |
| **First-class editable** | draw.io XML (.drawio) | refine | Own mxGraph XML writer from positioned IR |
| **Adapter** (full support, optional deps) | PDF (Playwright print-to-PDF) · PPTX (python-pptx) | publish / refine | Optional extras `[pdf]`, `[pptx]` |
| **Best-effort** (lossy, capability-reported) | Mermaid source · PlantUML source · (later, if wanted: Excalidraw JSON, BPMN XML with watermark warning) | regenerate / interop | DSL writers from logical IR |
| **Rejected** | EMF (Windows-only Inkscape path, text→paths), SVG-ungroup-in-PowerPoint as *primary* editable path (manual, regression-prone), CairoSVG anything | — | Documented in limitations |

## 2. First-Class Details

**SVG (canonical)** — self-contained by default: embedded subset WOFF2 fonts; options: `textAsPaths`, `embedSpec` (spec JSON in `<metadata>` for provenance/re-import), deterministic ids/ordering (diffable golden files).
**PNG** — Chromium screenshot, `scale` (deviceScaleFactor), transparent or themed background.
**HTML gallery** — static site: index grid → per-diagram page (inline SVG, spec source, render report, download links). Doubles as E2E fixture (`09-…md`).
**JSON spec** — round-trip guarantee: spec → render is pure; artifacts embed spec hash + engine versions (NFR-1/6).

## 3. Editable Outputs (the PowerPoint answer)

**draw.io writer (primary editable):**
- Native `swimlane` pool/lane cells (verified style keys), container parent/child, exact geometry from positioned IR, orthogonal edge points as `mxPoint` arrays, `writingDirection=rtl` where labels demand.
- Constraint: stick to documented/verified style-key subset (R-14); uncompressed XML for portability.
- Round-trip test: output opened/exported headless by draw.io CLI in CI (validation only, not in render path — R-18).
- User flows: edit in diagrams.net/desktop; or insert into PowerPoint via draw.io M365 add-in.

**PPTX writer (PowerPoint-native):**
- python-pptx: autoshapes + text frames + connectors (straight/elbow) + freeforms for complex outlines; EMU coordinates converted from IR px; group per container/lane; slide sized to diagram or template.
- RTL: `rtl="1"` paragraph patch + alignment + font name (PowerPoint shapes Arabic itself — verified).
- Declared fidelity ceilings (R-16): no gradients-parity guarantee, curved-edge approximation (elbow or freeform), fonts must exist on the viewing machine (no embedding via python-pptx) — all listed in CapabilityReport per export.
- `drawio2pptx` (alpha) noted as watch-item, not a dependency.

**Manual path documented for users**: SVG → PowerPoint Insert → Ungroup → "Convert to Shape" (M365/2019+; works, but text editability depends on SVG text encoding; transient ribbon regression noted in 2511 builds).

## 4. Source Exports (best-effort, explicit loss)

Writers traverse *logical* IR (positions dropped by design). Per-export CapabilityReport lists dropped features (lanes→Mermaid: unsupported → emitted as subgraph approximation + warning; ports → dropped; styles → nearest classDef/skinparam). Arabic: Mermaid diacritics workaround (quote/strip + warning, #3047); PlantUML flagged UNVERIFIED-bidi. These exports exist for ecosystem interop and human migration, never as fidelity paths.

## 5. Rendering Layer Mechanics

- Programmatic SVG construction (no string templates): shape library (rect, rounded, stadium, diamond, cylinder, person/C4, lane band, note, …), arrowhead defs library, label block with wrapping (measured lines), z-order: lanes → groups → edges → nodes → labels → annotations.
- RenderReport: warnings (overflow, dropped hints), error capture, crossing/overlap counts, timing; non-zero exit + machine-readable report on failed render (NFR-4).
- Browser involvement is *export-time only*; SVG generation itself is pure Python (fast unit tests).

## 6. Export Metadata

Every artifact: `generator`, engine version, spec hash, specVersion, theme id, font set, layout engine + version, timestamp — embedded (SVG `<metadata>`, PNG tEXt, PDF XMP where practical, PPTX core properties, drawio file comment).
