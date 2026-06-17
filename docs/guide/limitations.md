# Limitations & known ceilings

An honest list of what Tarseem does not (yet) do, and the fidelity ceilings of each export. Every
runtime ceiling is also reported machine-readably in a writer's `CapabilityReport` (invariant 6),
never silently dropped.

## Scope

- **Families:** flowchart, sequence, architecture/C4, deployment, state, ER, class, mind map,
  swimlane/process, dependency, activity. Other notations are addable as plugins
  ([extending/clone-a-type.md](../extending/clone-a-type.md)) rather than shipped.
- **Schema version:** only `specVersion` `1.x` is accepted. A `0.x` spec is rejected (`E_VERSION`) —
  upgrade it with `tarseem migrate` (ADR-009).
- **No network at render time.** Kroki is an optional, off-by-default extra; nothing else calls out.
- **Performance target:** ≤100 nodes render ≤2 s warm; ≤300 nodes supported. Larger graphs work but
  are not performance-tuned.

## Layout

- **Sequence** diagrams use a deterministic Python layouter, not ELK (by design).
- **Nested lanes** are best-effort (AM-6): parent group bands are drawn, but deep nesting is not
  fully optimised.
- **Radial mind maps** are for balanced/shallow trees only; deep/uneven trees use `mrtree` (the
  default). A node-overlap safety net runs, but it does not resolve node↔edge grazes in a deep
  radial wedge — the family steers you to `mrtree` instead (spike-6).
- The **libavoid** rerouter is optional and experimental (`layout.router="libavoid"`, ADR-006);
  ELK orthogonal routing is the default.

## Arabic / RTL

- Fully shaped, joined, mirrored, and pixel-stable across SVG/PNG/PDF and the editable writers.
- **PDF text layer:** the *picture* is correct, but extracted/searchable Arabic text is **not**
  reliable — Chromium prints shaped Arabic as Type3 visual-order glyphs with no logical Unicode. A
  searchable layer was investigated and deferred (spike-5); the PDF stays visual-only for Arabic.

## Exports

| Format | Ceiling |
|---|---|
| **SVG** | none — the canonical artifact. |
| **PNG / PDF** | faithful raster/print of the SVG. PDF Arabic is not searchable (above). |
| **draw.io** | lanes are explicit static rects, **not** draggable swimlane containers (ADR-007); orthogonal edges only (no curved); ER ports folded into labels. Font embedded (renders Cairo with zero setup); a draw.io install without Cairo falls back to sans. |
| **PPTX** | **fonts not embedded** — install Cairo to render Arabic/Cairo correctly; curved edges approximated by sampled segments; no gradients. |
| **Mermaid / PlantUML** | **deferred to a future feature** — best-effort source exports are designed (lossy, capability-reported) but not shipped. |

## Editability

- `draw.io` and `pptx` open and are hand-editable, but reproduce the canonical SVG geometry
  (ADR-005/007) rather than offering native semantic containers in every case (see the table).

See [troubleshooting.md](troubleshooting.md) for diagnosing failures, and each writer's
`*.report.json` sidecar for the exact per-diagram fidelity.
