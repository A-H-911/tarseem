# Phase 2 — Acceptance-Criteria Progress

Work order (per kickoff): **A1 → A5 → A2 → A12 → A3 → A4 → A11**. TDD: failing tests → implement → green.
Review stops: after **A1–A5 green**, and at **Phase 2 exit (A1–A5 + A11 + A12-LTR)**.

| # | Criterion | Status | Tests | Evidence / golden | Notes |
|---|---|---|---|---|---|
| A1 | Spec validation (coded, path-precise) | ✅ green | `tests/test_a1_validation.py` (13) | validation demo (valid→ok; invalid→`E_SCHEMA`/`E_BAD_REF`/`E_DUP_ID`…) | core schema 2020-12 + 4-layer `validate()`; pure |
| A5 | Basic styling (theme + overrides + presets) | ✅ green | `tests/test_a5_styling.py` (9) | cascade unit tests | deep-merge cascade theme→overrides→group→lane→styleRefs→inline; golden render lands with A2 |
| A2 | Flowchart / architecture-C4 / dependency via ELK | ✅ green | `tests/test_a2_render.py` (12) | `phase-2-goldens/{flowchart,architecture,dependency}.{svg,png}` | full pipeline compile→measure(uharfbuzz)→ELK→SVG→PNG; ELK JSON confined to adapter; edge labels at routed-polyline midpoint |
| A12 | Swimlane LTR (ref-1 + ref-3) | ✅ green | `tests/test_a12_swimlane.py` (12) | `phase-2-goldens/swimlane-{bug-triage,pipeline}.{svg,png}` | lane-grid layouter (pure Python, no ELK); title bar + pills + hue tints + badges + UML markers + back-edge/dashed routing; reuses A2 shape/font primitives |
| A3 | SVG + PNG deterministic | ✅ green | `tests/test_a3_determinism.py` (5) | cross-hash-seed digest match | two font-subset nondeterminism sources fixed: (1) sorted codepoints vs PYTHONHASHSEED, (2) `recalcTimestamp=False` so `head.modified` keeps the bundled font's fixed value instead of wall-clock time on save; SVG byte-identical across runs + PNG bytes stable |
| A4 | Clean Python API + CLI | ✅ green | `tests/test_a4_api.py` (11) | `Engine().render(spec).export(["svg","png"])` + `tarseem` CLI | facade dispatches swimlane→lanegrid, graph→ELK; provenance (spec-hash + versions) embedded (invariant 7) |
| A11 | `engine doctor` | ✅ green | `tests/test_a11_doctor.py` (9) | `tarseem doctor` (+`--json`) | verifies node/elkjs(pinned 0.11.1)/Playwright-Chromium/Cairo font; every failure carries an actionable hint; exit 0/1 |

**Phase-2 exit reached — A1–A5 + A11 + A12-LTR all green.** Full suite 77 passed; ruff + mypy clean.

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

## A12 — evidence
Swimlane uses the **lane-grid layouter** (`layout/lanegrid/`), pure Python — NOT ELK
(Phase-0 spike-3 proved ELK partitioning groups by flow axis, not lanes). One step per
column = topological number; lanes = fixed rows; from-scratch orthogonal router exploits
one-step-per-column so long cross-lane + back-edges avoid nodes.

Goldens reproduce the acceptance references (visual contract `references/analysis.md`):
- **swimlane-bug-triage** (Reference-1, 4 lanes): title bar, header pills, hue tints,
  numbered badges (start/terminal exempt), stadium/diamond/roundrect, back-edge (`fails`)
  + long cross-lane edges (`no`, `passes`).
- **swimlane-pipeline** (Reference-3, 3 lanes): full shape set
  (parallelogram/diamond/roundrect/cylinder/document), UML start/end markers, dashed
  `async` edge, `bad` back-edge loop, long Save→Receipt edge.

Shape-aware badge/edge geometry: badges shift clear of non-rect corners (`_badge_baseline`
for the cylinder cap, `_badge_x` for the parallelogram skew) and edges attach to real shape
sides (`_side_x`) so arrows touch the parallelogram body without a gap. SVG output is
well-formed XML (no duplicate attrs) so strict viewers accept it.
Per-lane theming = palette function over invariant geometry (binds F4 later). RTL variant
is geometry-only and gated to Phase 4 (F3).

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
