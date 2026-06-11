# Acceptance Criteria

Status: Proposed · 2026-06-11 · All items are testable; each maps to CI checks or gate checklists.

---

## MVP Acceptance (end of Phase 3)

| # | Criterion | Verification |
|---|---|---|
| A1 | Validated JSON specs accepted; invalid specs rejected with path-precise, coded errors | schema test corpus |
| A2 | Renders flowchart, architecture/C4, and dependency diagrams from spec via ELK | golden samples |
| A12 | **Swimlane (D3:B)**: horizontal lanes w/ title bar, header pills, per-lane hue theming, auto-number badges, reference shape set (stadium/diamond/parallelogram/cylinder/document + UML markers), cross-lane orthogonal edges incl. back-edges — Reference-1 and Reference-3 reproduced (LTR; RTL variant gated in Phase 4) | side-by-side vs `references/` + golden |
| A3 | SVG + PNG export, deterministic across runs (same versions) | repeat-render diff test |
| A4 | Clean Python API: `Engine().render(spec).export(["svg","png"])` + CLI equivalents | API tests + docs quickstart |
| A5 | Basic styling: theme + node/edge-level overrides + named presets functional | unit + golden |
| A6 | Browser gallery builds; all samples render error-free in Chromium | E2E |
| A7 | Automated tests at schema/unit/contract/render/E2E levels in CI | CI config |
| A8 | Green on ≥1 OS with documented path (and CI bootstrapped) for Win/macOS/Linux | CI matrix |
| A9 | Documented examples for every MVP family (gallery = docs fixtures) | doc build |
| A10 | Sequence diagrams render via deterministic layouter | golden samples |
| A11 | `engine doctor` verifies Node/elkjs/Playwright/fonts and reports actionable failures | doctor tests |

## Full Target Acceptance (end of Phase 7)

| # | Criterion | Verification |
|---|---|---|
| F1 | Major families supported: flowchart, sequence, architecture/C4 (context+container+component), deployment/infrastructure, state, ER, class, activity, mind map, swimlane/process, dependency | gallery completeness check |
| F2 | Arabic + RTL reliable: shaping, mixed-script, mirroring (RL), lane headers, exports — pixel-stable on 3 OS | Arabic golden suite |
| F3 | Swimlanes: horizontal + vertical lanes, phases, per-lane styling, cross-lane orthogonal flows, **RTL variant (Reference-2: headers right, mirrored badges, right→left flow, shaped Arabic incl. diacritics)**; nested lanes best-effort | side-by-side gate + metrics |
| F4 | Styling: full 6-level cascade, themes portable across SVG/drawio/PPTX writers (within declared ceilings) | cross-writer golden checks |
| F5 | Routing: orthogonal+curved modes, ports, waypoints, priorities; measured crossing counts within thresholds on benchmark set | RenderReport gates |
| F6 | Cross-platform: full suite green on Windows, macOS, Linux | CI matrix |
| F7 | Exports: SVG/PNG/PDF/HTML first-class; drawio + PPTX editable (open + edit verified); Mermaid/PlantUML best-effort with loss reports | export suites + manual gate |
| F8 | Browser verification: gallery + E2E + screenshot regression operational and gating | CI |
| F9 | Extensibility: new diagram type added via plugin without core changes (proven twice, incl. clone-tutorial) | plugin exercise |
| F10 | Documentation complete per `10-documentation-plan.md`, including limitations + troubleshooting | doc review gate |
| F11 | Agent-ready: pure-function generate API, JSON errors, published schema bundle, reference slash-command/skill integration | integration example test |
| F12 | Schema v1.0 frozen with versioning + migration tooling | migration tests |
