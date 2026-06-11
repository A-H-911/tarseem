# Architecture Recommendation & Internal Component Model

Status: Recommended, pending approval · 2026-06-11
This is the central ADR. Decisions here trace to `03-engine-comparison.md` findings and `02-risks.md` mitigations.

---

## 1. Core Decision: "Compile, don't transpile"

Two candidate architectures were evaluated:

**A. DSL transpiler** — compile JSON specs into Mermaid/PlantUML/D2 text and let those tools render.
*Rejected as core*: no swimlanes (Mermaid/D2) or horizontal lanes (PlantUML), broken/unverified Arabic (R-6), no ports/manual positions, styling ceilings, no editable output. Retained as best-effort source-export adapters only.

**B. Schema compiler** (RECOMMENDED) — the Python engine owns an internal model (IR), delegates **geometry** to ELK, renders **SVG itself**, verifies/rasterizes in **Chromium (Playwright)**, and **writes editable formats directly** (draw.io XML, PPTX) from the same positioned IR.

The decisive insight: once layout is computed, *every* target (SVG, PNG, PDF, draw.io, PPTX, gallery) is a cheap serialization of one positioned IR. Editability stops being a conversion problem and becomes a writer problem. This single-layout/multi-writer property is what no off-the-shelf engine offers.

### What the wrapper owns vs. delegates

| Owns (Python) | Delegates |
|---|---|
| JSON schema, validation, semantic lint | Graph layout & edge routing → **ELK (elkjs)** |
| Internal model (IR) + diagram-type compilers | Raster/PDF + text shaping at render → **Chromium via Playwright** |
| Text measurement (uharfbuzz; Arabic-aware) | Optional fallback layout → **Graphviz dot** |
| Theme/style resolution (6-level cascade) | Optional fast PNG (Latin-only) → **resvg** |
| SVG generation (canonical renderer) | Optional text-to-path → **Inkscape / fonttools pipeline** |
| Sequence-diagram layout (deterministic) | Optional DSL rendering → **Kroki / local CLIs** |
| draw.io XML writer, PPTX writer, Mermaid/PlantUML writers | |
| Gallery, tests, docs, plugin registry | |

## 2. Pipeline

```
 JSON spec ──► Schema validation ──► Semantic validation ──► IR (normalized)
                                                              │
                                              diagram-type compiler (plugin)
                                                              │
                                      text measurement (uharfbuzz, fonts)
                                                              │
                              ┌── graph families ──► ELK JSON ──► elkjs (Node subproc) ──► positions
                   layout ────┤── sequence ────────► deterministic layouter (Python)
                              └── fixed/manual ────► passthrough + libavoid-class routing (future)
                                                              │
                                                   POSITIONED IR (single source of truth)
              ┌───────────────┬───────────────┬───────────────┼────────────────┬──────────────┐
              ▼               ▼               ▼               ▼                ▼              ▼
        SVG renderer    draw.io writer   PPTX writer    Mermaid/PlantUML   HTML gallery   JSON sidecar
              │            (editable)      (editable)    writers (lossy)        │          (metadata)
              ▼                                                                 ▼
     Playwright/Chromium ──► PNG · PDF · screenshots ──► visual regression & E2E
```

## 3. Layer Model (refines the 11 proposed layers)

| # | Layer | Responsibility | Key tech | Notes vs. proposal |
|---|---|---|---|---|
| 1 | **Schema** | JSON Schema 2020-12 core + per-type extensions; versioning | `jsonschema` | As proposed; see `05-schema-strategy.md` |
| 2 | **Validation** | structural → referential → semantic → capability (per target adapter) | own code | "Export/render capability validation" realized as capability negotiation |
| 3 | **Diagram Model (IR)** | typed dataclasses: Node, Edge, Container, Lane, Port, Label, Style, Waypoint; positioned variant after layout | own code | Two states: *logical IR* and *positioned IR* |
| 4 | **Diagram-type plugins** | compile spec-type → logical IR; provide layout/render/export profiles | registry | Merges proposed "Adapter/Plugin" with type system |
| 5 | **Layout & Routing** | ELK option mapping, partitioning for lanes, ports, RTL mirroring (direction=LEFT), routing hints; sequence layouter | elkjs subprocess (pinned), Graphviz fallback | Long-lived Node proc, ELK JSON contract |
| 6 | **Theme & Style** | cascade resolution to concrete per-element styles before rendering; fonts incl. Arabic stack | own code | Backend-neutral resolved styles keep themes portable (FR-5.4) |
| 7 | **Rendering** | positioned IR → SVG (shapes lib, arrowheads, labels with `direction="rtl"`, embedded fonts) | own code (Jinja-free, programmatic SVG) | "Collect logs/detect failed renders" = render report object |
| 8 | **Export** | writers: SVG/PNG/PDF/HTML/drawio/PPTX/Mermaid/PlantUML; export metadata (spec hash, engine versions) | Playwright, python-pptx, lxml | Four roles: publish/refine/regenerate/verify |
| 9 | **Gallery/Preview** | static HTML index of all samples; per-diagram page (SVG + spec + report); screenshot capture | Playwright | Doubles as the E2E fixture |
| 10 | **Test** | schema/unit/adapter-contract/render/export/visual-regression/E2E; 3-OS CI matrix | pytest, Playwright, pixel+SSIM diff | See `09-…md` |
| 11 | **Documentation** | generated schema docs, ADRs, guides | mkdocs (proposed) | See `10-…md` |

## 4. Adapter Boundaries (contracts)

1. **LayoutAdapter**: `layout(LogicalIR, LayoutProfile) -> PositionedIR`. Implementations: `ElkLayout` (primary), `SequenceLayout`, `GraphvizLayout` (fallback), `FixedLayout` (manual positions). Contract tests run against all.
2. **RenderAdapter**: `render(PositionedIR, ResolvedTheme) -> SvgDocument + RenderReport`.
3. **ExportWriter**: `write(PositionedIR | SvgDocument, ExportOptions) -> Artifact + CapabilityReport` (drops are *reported*, never silent — FR-1.6, R-19).
4. **Capability descriptors**: every adapter publishes `supports = {ports, lanes, curvedEdges, rtlMirror, …}`; validation layer cross-checks spec features against the chosen pipeline before work starts.

## 5. Extension Model (Phase 7 target, architecture from day 1)

A new diagram type = one plugin package providing:
- `schema/<type>.extension.json` (extends core schema via `$ref` + `x-diagram-type`)
- `compiler.py` (spec → logical IR)
- `layout_profile.py` (ELK options / custom layouter selection)
- `render_profile.py` (shape set, default theme bindings)
- optional `export_overrides.py` (e.g., PlantUML writer mapping)
Built-ins use the exact same mechanism (dogfooding guarantees no monolith — FR-9.4). Cloning a type = copying its plugin and editing profiles (FR-9.3). Registration via entry points (`diagram_engine.types`).

## 6. Answers to the 10 Expected-Recommendation Questions

1. **One backend or multiple?** Multiple, with strict roles: ELK (layout), own SVG (render), Chromium (raster/verify), draw.io-XML + python-pptx (editable), Graphviz (fallback), Mermaid/PlantUML (lossy source export). No single engine satisfies the scope (verified).
2. **Primary MVP target?** ELK + own SVG renderer + Playwright, for flowchart/architecture/C4 families.
3. **Advanced layout/routing?** ELK layered with orthogonal routing, ports, partitioning; libavoid evaluated in Phase 5 for post-hoc routing refinement if ELK residual crossings unacceptable (R-8).
4. **Editable output?** draw.io XML writer (primary; native lanes, RTL keys) + PPTX writer (PowerPoint-native shapes). Both from positioned IR.
5. **Browser gallery validation?** Playwright/Chromium (also the Arabic-correct rasterizer; one dependency, two jobs).
6. **Realistic for MVP?** *(updated per D3:B)* 4 families — flowchart, architecture/C4, dependency, **swimlane (LTR, reference-style)** — JSON schema v0, validation, ELK layout (swimlane path decided by Phase 0 spike), SVG+PNG, basic styling + per-lane theming, gallery seed, 1-OS green CI, clean Python API.
7. **Deferred?** Sequence (P3), RTL full validation incl. RTL swimlane (P4), routing-hint depth + remaining families (P5), PDF+editable exports — drawio & PPTX in parallel per D2:C (P6), plugins-as-public-API (P7), nested lanes (best-effort), avoid-zones (best-effort).
8. **Risky / may require custom implementation?** Swimlane fidelity beyond ELK partitioning (R-9 — fallback: own lane-grid layouter); label-collision avoidance (R-13); portable-SVG text-to-path pipeline (R-1); PPTX fidelity ceilings (R-16); Mermaid/PlantUML export lossiness (R-19).
9. **Unavoidable trade-offs?** Node+Chromium as managed deps in exchange for layout quality and Arabic correctness; editable exports are fidelity-bounded; determinism requires version pinning; one schema means some family-specific features stay extension-local. (Full list: `02-risks.md` §3.)
10. **First implementation path after approval?** Phase 0 spikes (1: elkjs subprocess round-trip; 2: Arabic SVG via uharfbuzz measure + Chromium render; 3: ELK-partitioning swimlane sample; 4: draw.io XML lane file opens correctly) → then Phase 1 baseline. See `11-phased-plan.md`.

## 7. Rationale Summary for Selected Backends

- **ELK/elkjs**: only OSS layout engine with first-class ports, compound nodes, partitioning, orthogonal routing + crossing minimization, and a JSON service contract; actively maintained (0.11.1, 03/2026); EPL-2.0; embedding pattern proven by Mermaid, D2, draw.io, capellambse.
- **Own SVG renderer**: every requirement that killed off-the-shelf renderers (6-level styling, Arabic `direction`, font embedding, lane bands, theme portability) is straightforward when we emit the SVG ourselves from positioned geometry.
- **Playwright/Chromium**: verified HarfBuzz shaping; PNG/PDF/screenshots; cross-platform without Xvfb; Apache-2.0; also the E2E harness — one dependency serving render, export, and test layers.
- **draw.io XML + python-pptx writers**: the only two paths that yield genuinely *editable* artifacts (native lanes / native PowerPoint shapes) without commercial or watermarked dependencies; both consume our computed geometry so the edited file starts pixel-equal to the published one.
- **Graphviz fallback**: protects against Node-hostile environments at documented fidelity cost; mature Python bindings.
