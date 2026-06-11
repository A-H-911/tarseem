# Ambiguity & Risk Analysis

Status: Draft for approval · 2026-06-11
Likelihood/Impact: L/M/H. "Affects" = MVP, Full, or both.

---

## 1. Ambiguities & Hidden Assumptions

| # | Ambiguity | Resolution path |
|---|---|---|
| AM-1 | ~~Reference images not attached~~ **Resolved (D9)**: 3 images provided; features extracted in `references/analysis.md`, bound to A12/F3 | Closed 2026-06-11 |
| AM-2 | "Editable for PowerPoint" can mean: SVG ungroup-to-shapes, native PPTX shapes, or draw.io round-trip | Treat all three as distinct paths; PPTX-native + draw.io are primary (D2) |
| AM-3 | "Minimize or prevent crossings" — prevention is impossible in general (non-planar graphs) | Requirement re-stated as: automatic minimization + hints; zero-crossing not guaranteed |
| AM-4 | 17 diagram families listed; several overlap (architecture/context/integration/infrastructure are one rendering family) | Families consolidated into ~8 engine-level families (FR-3) |
| AM-5 | "Browser-based verification" — interactive gallery vs. automated E2E | Both: static gallery + Playwright E2E/screenshots |
| AM-6 | Nested lanes "where practical" — no mainstream engine renders nested lanes well | Declared best-effort/Full; explicit limitation doc |
| AM-7 | Agent/slash-command integration unspecified | Phase 7 defines integration points; out of MVP |
| AM-8 | Performance/size targets unstated | NFR-2 proposed (≤100 nodes ≤2 s warm); confirm |

## 2. Technical Risks

### Rendering & RTL

| ID | Risk | Imp. | Lik. | Mitigation | Affects |
|---|---|---|---|---|---|
| R-1 | **Arabic breaks outside browsers**: SVG with Unicode text renders wrong in non-shaping renderers (CairoSVG unsupported; resvg partial — no Arabic fallback shaper; Batik no bidi) | H | H (certain without mitigation) | Canonical raster path = Playwright/Chromium (HarfBuzz, verified). Portable SVG = embedded fonts + optional text-to-path (uharfbuzz+fonttools or Inkscape). Ban CairoSVG. | Both |
| R-2 | Node auto-sizing wrong for Arabic (engines measure LTR metrics) | H | H | Own text measurement in Python (uharfbuzz advances; Pillow+raqm cross-check) feeding ELK width/height inputs | Both |
| R-3 | Windows text measurement gap: Pillow raqm needs manual `fribidi.dll`; silent fallback | M | M | Primary measurer = uharfbuzz (no fribidi needed for shaping); `doctor` command checks `features.check_feature('raqm')` if Pillow path used | Both |
| R-4 | Headless CI lacks Arabic fonts → tofu/garbage in screenshots | M | H | Bundle OFL fonts (Cairo/Tajawal/Noto Arabic) in package; embed via data-URI `@font-face`; CI font install documented | Both |
| R-5 | Double-shaping corruption if arabic-reshaper output reaches a shaping renderer | M | M | Architecture rule: pre-shaping only inside non-shaping export adapters, never in IR | Both |
| R-6 | Mermaid parser crashes on Arabic diacritics (issue #3047, unresolved since 2022; partial PR #3432 introduced regressions) | M | H | Mermaid is best-effort source export only, never the Arabic rendering path; strip/quote diacritics on export with warning | Full |
| R-7 | PDF Arabic fidelity varies | M | M | PDF via Chromium print-to-PDF (shaping verified); WeasyPrint as alternative; both Pango/HarfBuzz-class | Full |

### Layout & Swimlanes

| ID | Risk | Imp. | Lik. | Mitigation | Affects |
|---|---|---|---|---|---|
| R-8 | ELK cross-hierarchy edge routing produces avoidable crossings (known, partly wontfix #503/#401) | M | M | Keep hierarchy shallow in compiled graphs; route inter-container edges at LCA; accept residual; libavoid post-routing as Full-phase option | Both |
| R-9 | ELK partitioning ≠ full swimlane semantics (geometry only; lane bands drawn by us; vertical+horizontal grids need composition) | H | M | Phase 0 spike rebuilds the 3 reference diagrams via ELK partitioning before committing; fallback (pre-approved) = fixed-grid lane layout in Python + ELK per-lane sublayouts. **D3:B makes this MVP-critical** — spike outcome decides the MVP layout path | **MVP** (was Full) |
| R-10 | elkjs is GWT-transpiled JS — needs Node subprocess; cold start, packaging friction | M | H | Long-lived subprocess + JSON stdin/stdout (pattern proven by capellambse); vendor pinned elkjs bundle; mini-racer in-process as alternative | Both |
| R-11 | dagre structurally weak (no ports/compound; cluster bugs) — anything built on it inherits limits | M | H | dagre not used; ELK primary, Graphviz fallback | Both |
| R-12 | Sequence diagrams don't fit graph layout engines | M | H | Own deterministic lifeline/message layout in Python (well-understood, low risk) | MVP/P3 |
| R-13 | No engine guarantees label-overlap-free routing | M | M | ELK label placement options; post-layout label collision pass; document limitation | Full |

### Export & Editability

| ID | Risk | Imp. | Lik. | Mitigation | Affects |
|---|---|---|---|---|---|
| R-14 | draw.io style-string format has **no formal spec**; keys reverse-engineered | M | M | Constrain writer to documented/verified subset (swimlane;, writingDirection, geometry); golden-file round-trip tests opening output in draw.io CLI | Full |
| R-15 | drawpyo immature (v0.2.x alpha, no swimlane API, no RTL API) | L | H | Own thin mxGraph XML writer (format is simple XML); drawpyo not a dependency | Full |
| R-16 | PPTX fidelity: connectors/fonts/curves degrade vs SVG; python-pptx has no RTL API | M | M | Positioned-IR → native shapes keeps geometry exact; `rtl="1"` via lxml patch (verified pattern); accept documented fidelity limits | Full |
| R-17 | PowerPoint "Convert to Shape" regression risk (transient removal in build 2511) + text editability loss on SVG ungroup | L | M | Primary editable path = native PPTX + draw.io, not SVG-ungroup | Full |
| R-18 | draw.io CLI headless needs Xvfb/--no-sandbox in CI; PNG failures reported | L | M | draw.io CLI used only to *validate* our XML in tests, not in render path; Docker image rlespinasse/drawio-export | Full |
| R-19 | Source exports (Mermaid/PlantUML) can't express full IR (lanes, ports, exact positions) | M | H (certain) | Declared lossy/best-effort; capability report enumerates dropped features per export | Full |

### Platform, Dependencies, Licensing

| ID | Risk | Imp. | Lik. | Mitigation | Affects |
|---|---|---|---|---|---|
| R-20 | Dependency stack (Node + elkjs + Playwright/Chromium + fonts) is heavy for end users | M | M | `pip install` core + `engine doctor` + extras (`[layout]`, `[browser]`); Docker reference image; document offline installs | Both |
| R-21 | Engine version drift changes layouts (breaks visual regression + determinism) | M | H | Pin elkjs/Playwright versions; record versions in artifact metadata; regenerate baselines on upgrade as explicit PR | Both |
| R-22 | License traps: OGDF GPL, GoJS $3,995 commercial, TALA commercial, JointJS+ commercial, bpmn-js mandatory watermark | H | M | Excluded from required path (NFR-3); bpmn-js only as optional opt-in adapter with watermark warning | Both |
| R-23 | PlantUML single-maintainer + Java dependency | L | M | PlantUML optional adapter only (source export / legacy interop), never core | Full |
| R-24 | Kroki centralizes many engines but can't pin individual engine versions; network dependency | L | M | Kroki = optional convenience backend, off by default (NFR-7) | Full |
| R-25 | Windows-only steps (Inkscape→EMF) violate cross-platform rule | L | H | EMF path excluded; PPTX-native instead; Inkscape only optional | Full |

### Schema & Scope

| ID | Risk | Imp. | Lik. | Mitigation | Affects |
|---|---|---|---|---|---|
| R-26 | Unified schema too generic (useless) or too rigid (unextendable) — the central design tension | H | M | Core-+-profile model (`05-schema-strategy.md`): small stable core, typed extensions, per-adapter capability negotiation; schema reviewed against 8 families before freeze | Both |
| R-27 | Scope breadth (8+ families × 6 exports × 3 OS × RTL) stalls delivery. **D3:B deliberately widens MVP to 4 families incl. the highest-risk one (swimlane)** — accepted by owner with eyes open; Phase 0 spike is the pressure valve | H | M→H | Strict phase gates; MVP = 4 families, SVG+PNG, 1 OS green; matrix grows per phase; spike-decided swimlane path before Phase 2 commits | Both |
| R-28 | AI-generated specs produce invalid/degenerate diagrams | M | H | Strict validation with path-precise errors, semantic lint warnings, `--repair` suggestions; JSON (not DSL) input is itself the mitigation | Both |
| R-29 | Spec evolution breaks stored diagrams | M | M | `specVersion` + additive-only minor changes + migration scripts from v1.0 | Full |

## 3. Conflicting Requirements (acknowledged trade-offs)

1. **Editable text vs. universal fidelity** (SVG): embedded-font text stays editable but requires capable renderers; text-to-path renders everywhere but freezes text. → Both offered as export options; default = embedded fonts.
2. **One schema vs. per-family expressiveness**: resolved via core+extensions, accepting that some family features never generalize.
3. **Layout determinism vs. engine upgrades**: pinning wins; upgrades are deliberate baseline-regen events.
4. **Cross-platform purity vs. best tooling**: Node/Chromium accepted as managed dependencies (D1) rather than rejecting the best engines.
5. **Static-image sufficiency explicitly rejected** by brief → editable adapters are mandatory Full-scope, accepting their fidelity ceilings (R-16, R-19).
