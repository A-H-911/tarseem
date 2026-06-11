# Phase 2 — Acceptance-Criteria Progress

Work order (per kickoff): **A1 → A5 → A2 → A12 → A3 → A4 → A11**. TDD: failing tests → implement → green.
Review stops: after **A1–A5 green**, and at **Phase 2 exit (A1–A5 + A11 + A12-LTR)**.

| # | Criterion | Status | Tests | Evidence / golden | Notes |
|---|---|---|---|---|---|
| A1 | Spec validation (coded, path-precise) | ✅ green | `tests/test_a1_validation.py` (13) | validation demo (valid→ok; invalid→`E_SCHEMA`/`E_BAD_REF`/`E_DUP_ID`…) | core schema 2020-12 + 4-layer `validate()`; pure |
| A5 | Basic styling (theme + overrides + presets) | ✅ green | `tests/test_a5_styling.py` (9) | cascade unit tests | deep-merge cascade theme→overrides→group→lane→styleRefs→inline; golden render lands with A2 |
| A2 | Flowchart / architecture-C4 / dependency via ELK | ✅ green | `tests/test_a2_render.py` (12) | `phase-2-goldens/{flowchart,architecture,dependency}.{svg,png}` | full pipeline compile→measure(uharfbuzz)→ELK→SVG→PNG; ELK JSON confined to adapter; edge labels at routed-polyline midpoint |
| A12 | Swimlane LTR (ref-1 + ref-3) | ⏳ next | — | — | lane-grid path (Phase-0 decision); reuse spike-3 |
| A3 | SVG + PNG deterministic | ⬜ | — | — | repeat-render byte-diff |
| A4 | Clean Python API + CLI | ⬜ | — | — | `Engine().render(spec).export([...])` |
| A11 | `engine doctor` | ⬜ | — | — | Node/elkjs/Playwright/fonts checks |

## A2 — evidence
Three families render via ELK through one positioned IR (one IR, many writers):

```
spec → validate → compile_spec (LogicalGraph, styles resolved)
     → measure_graph (uharfbuzz shaped advances → node sizes, BEFORE layout)
     → ElkLayout.layout (vendored elkjs 0.11.1 subprocess; ELK JSON in-adapter) → PositionedDiagram
     → render_svg (canonical SVG, embedded WOFF2 subset) → svg_to_png (Chromium)
```

Goldens (`docs/spikes/phase-2-goldens/`):
- **flowchart** (TB, 7 nodes): stadium/roundrect/diamond, orthogonal edges, back-edge, `yes`/`no`/`retry` labels at route midpoints.
- **architecture** (LR, 6 nodes): styled cylinder + event-bus (named presets, A5 cascade live), `HTTPS`/`gRPC`/`SQL`/`publish`/`consume` labels.
- **dependency** (LR, 6 nodes): multi-path DAG converging on `model`.

Invariants verified by test: `test_positioned_diagram_exposes_no_elk_json` (ELK keys never leak), `test_measure_*` (sizes set before layout), `test_layout_capability_report_declares_support` (elkjs 0.11.1 pinned).

## Invariants honored
- uharfbuzz measurement **before** layout (ADR-004); ELK JSON **only** inside the layout adapter (ADR-002);
  capability reports / coded errors, **never silent drops** (ADR-005 / 05 §4).

## A1 — evidence
Valid spec → `{"ok": true, "errors": [], "warnings": []}`.
Invalid spec (missing `specVersion`, bare-string label, dangling edge) →
```json
{"code":"E_SCHEMA","path":"/","message":"'specVersion' is a required property", ...}
{"code":"E_SCHEMA","path":"/nodes/0/label","message":"'oops' is not of type 'object'", ...}
```
(No render: A1's golden is the schema corpus, not an image.)
