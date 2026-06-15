# Phase 6 — Export & Editability — progress

Governing docs: `docs/plan/11-phased-plan.md` (Phase 6), `docs/plan/08-export-strategy.md`.
Exit: F5–F7 (`docs/plan/12-acceptance-criteria.md`) + an honest fidelity-ceiling table per
writer. Decision D2:C — draw.io and PPTX writers built in parallel (not sequential).

One positioned IR, many writers (ADR-001). New shared infra this phase: **CapabilityReport**
(invariant 6) on a single feature vocabulary, and deterministic **export provenance**
(invariant 7: no wall-clock timestamp — the §6 timestamp is deliberately omitted).

## Sub-stages

| # | Sub-stage | Status | Where |
|---|---|---|---|
| 0 | Shared infra: CapabilityReport + feature vocab; export metadata; `WriteResult`; logical-IR retained on `RenderResult`; `export()` writer dispatch + `.report.json` sidecars | ✅ done | `report.py`, `export/metadata.py`, `export/result.py`, `engine.py` |
| 1 | **draw.io writer** — native pool/lane swimlane cells, geometric lane parenting, exact geometry, floating `edgeStyle=none` edges with exact mxPoint routes, `writingDirection=rtl`, uncompressed XML, documented style-key subset, embedded provenance comment | ✅ done; **verified via Option-A (draw.io viewer) on 6 samples** | `export/drawio.py`, `tests/test_export_drawio.py`, `tools/verify_drawio.py` |
| 1a | **Render-fidelity loop (Option A)** — render each `.drawio` through draw.io's own viewer (mxGraph) in headless Chromium, screenshot, inspect. No install. | ✅ done | `tools/verify_drawio.py` |
| 1b | **Option B authoritative gate** — headless draw.io **Desktop** (Docker `rlespinasse/drawio-desktop-headless`) renders our `.drawio` | ✅ **executed locally — PASS** (6/6 render; Desktop agrees with viewer + SVG). CI workflow still unproven in CI. | `.github/workflows/drawio-roundtrip.yml`, `out/drawio-gate/` |

### Option-A verification findings (6 samples through draw.io's viewer)

4/6 clean on first pass; the oracle caught 2 real defects + 1 RTL ceiling — all addressed:
- **diamond rendered as a rectangle** — `rhombus=1` is not a shape name in mxGraph; fixed to `shape=rhombus;perimeter=rhombusPerimeter`. Confirmed rhombus after fix. Regression test added.
- **ER attribute rows were absent** while the CapabilityReport claimed "folded into label" (dishonest) — now genuinely folded as `<br>` lines with PK/FK tags; warning reworded to match. Confirmed + test.
- **RTL swimlane lane headers render on the LEFT** (draw.io `horizontal=0` can't mirror headers right for RTL) — flow/geometry mirror correctly, headers don't. Now an explicit `lanes` ceiling warning (not a silent mismatch). **Open decision for the user** (accept ceiling vs. pursue a non-native workaround).
- Minor: diamond label slightly overflows the rhombus outline (a diamond has ~half its bbox area). Cosmetic.

Verification is the **viewer** (Option A), not yet the Desktop editor (Option B) — those can differ; Option B is the final sign-off before human review.
| 2 | **PPTX writer** — python-pptx native shapes/connectors from IR in EMUs, `rtl="1"` lxml patch, deterministic zip, manual PowerPoint checklist | ✅ done (writer + tests); manual PPT review pending | `export/pptx.py`, `tests/test_export_pptx.py`, `docs/pptx-manual-checklist.md` |
| 3 | **PDF** via Chromium CDP (print-to-PDF, mirrors `png.py`) | ✅ done; visually verified vs canonical PNG (incl. Arabic) | `export/pdf.py`, `tests/test_export_pdf.py` |
| 4 | **Mermaid + PlantUML** source writers (logical IR) with CapabilityReports | ⛔ deferred → future feature (2026-06-15) | see "Deferred / future tasks" |
| 5 | Export metadata embedded in **all** artifacts (SVG already; PNG tEXt, PDF XMP, PPTX core-props, drawio done) | ◑ partial | drawio done |
| 6 | **class + mindmap** profiles (family/layout workstream; mindmap needs a non-layered ELK tree/radial algo — the real risk) | ⏳ | — |

Gate green throughout: ruff + mypy clean; `pytest` full suite passes; coverage 92% (≥80 gate).
New example specs deliberately NOT added — writers are exercised against the existing corpus
(`flowchart`, `swimlane-*`, `arabic-*`, `er-shop`) to avoid triggering 3-OS visual-baseline regen.

### Session decision (2026-06-15)

- **Sub-stage 4 (Mermaid + PlantUML) dropped → future feature** (see "Deferred / future tasks"). Plan,
  acceptance criteria, and requirements updated to match.
- **PPTX manual PowerPoint close-out: complete** — Arabic/English mixed-bidi spacing (review #3)
  owner-confirmed (see PPTX review round 1, updated).
- **Sub-stage 6 (class + mindmap)** and the remaining deferred items (PPTX font embedding,
  badge-as-circle, promote showcases) — **everything except spike-5 (searchable PDF, parked)** — are
  queued for **after a session cleanup**, in a later session.
- **Remaining active Phase-6 work:** sub-stage 5 (PNG `tEXt` + PDF `XMP` metadata) + verification/CI
  (linux/macOS baselines, Option-B CI) + `exports/` docs + PowerPoint workflow guide + merge.

## Bug-fix pass — user review round 1 (2026-06-13)

Six samples reviewed by the owner against the canonical `out/*.png`. Four draw.io-only defects
fixed + issue-named regression tests; verified through the viewer (and Desktop earlier):

| # | Issue | Fix | Test |
|---|---|---|---|
| 1/3 | RTL text not horizontally centered | `_style` forced `align=right`; dropped it (writingDirection only) — centered like the SVG | `test_rtl_node_label_is_centered_not_right_aligned` |
| 2 | draw.io ER lacked the table/theming of `out/er-shop.png` | ER entity now explicit table cells matching `render/er.py` (title bar, row separators, gold/blue PK/FK pills) | `test_er_renders_as_table_not_folded_label` |
| 3/4 | Numbered badge unsuitable (folded into label) | corner-circle badge (top-right for RTL, top-left for LTR) holding the number | `test_numbered_badge_is_a_corner_circle_not_folded`, `test_rtl_badge_circle_flips_to_right_corner` |
| 4 | start/end markers wrong style/colour | match `render/swimlane.py` — solid black start dot, bullseye end (ring + inner dot) | `test_end_marker_is_a_bullseye_with_inner_dot` |

Capability table updated: `badges` none→full (corner circle), `ports` none→partial (ER edges
anchored to rows via exact route), ER warning reworded. Full gate green; coverage 92.36%.

Example renders generated to `out/` for review (engine + draw.io): `vertical-release`,
`nested-delivery`, `tuned` (themed), `showcase-checkout-sequence` (new sequence spec, engine).

### Open items (owner sign-off)
- **Badge as circle in the canonical SVG too?** Currently SVG keeps corner *text* badges, draw.io
  uses circles → a visual divergence. Matching them means changing the SVG renderer → 3-OS
  visual-baseline regen (allowed via PR, invariant 7). **Deferred pending decision.**
- **Uniform node sizing** (bug #1, "left shapes not same size"): owner-marked optional → a
  measure-stage opt-in spec flag. **Deferred** (minimal-repro + RenderReport methodology when opted in).
- **Promote `showcase-checkout-sequence` (and other showcases) into `examples/`?** Adding to the
  golden corpus triggers gallery + 3-OS baseline machinery. Held in `out/` for now.
- **Minimal repro specs under `tests/regressions/`**: the issue-named tests above lock each fix
  against the existing example corpus (themselves minimal real reproductions); dedicated
  `tests/regressions/*.json` can be added if stricter isolation is wanted.

## Review round 2 (2026-06-13) — owner directives

- **Note 1 — review folder.** `out/` was a muddled mix (engine/viewer/desktop renders + drawio +
  sidecars across 4 subdirs). New `tools/build_review.py` builds **one** bundle `out/review/`:
  per diagram `<name>.engine.png` + `.drawio` + `.drawio.png` + `.report.json`, plus
  **`index.html`** (engine vs draw.io side-by-side). **`out/review/index.html` is the sign-off
  surface.** Convention: `examples/` = committed specs; `out/` = gitignored scratch.
- **Notes 2 + 5 — badge.** Auto-number badge is now a **corner circle in the canonical SVG and
  draw.io** (was SVG text / drawio circle). Default corner **switched: LTR→right, RTL→left**;
  opt-in override `theme.badgeCorner` = `auto|left|right`. win32 baselines regenerated
  (`scripts/regen_baselines.py`); **linux/macOS baselines still need regen** via
  `baselines.yml` workflow_dispatch before that CI goes green.
- **Note 3 — uniform node sizing.** Opt-in `layout.uniformNodeSize` (`true` | `"byShape"` |
  `{scope,width,height}`) in the measure stage; ER tables + fixed pseudostate markers exempt.
  Off by default ⇒ no baseline churn. Tests in `tests/test_uniform_node_size.py`.
- **Note 4 — themed examples for other families: DEFERRED to next turn** (depends on the review
  tool, now ready). Will add colored ER/sequence/state/deployment/dependency showcases and note
  any renderer theming gaps (e.g. ER title bar colour is currently hardcoded).

Full gate green; coverage 92.27%. New flags threaded: `compile_spec` carries `theme.badgeCorner`
into `diagram.theme`; `measure_graph` reads `layout.uniformNodeSize`.

## Review round 3 (2026-06-13) — 4 fixes

| # | Issue | Fix | Locus |
|---|---|---|---|
| 1 | cube label off-centre | label centres on the **front face** in BOTH writers: engine `_label_center`; draw.io `shape=cube;size=14;spacingTop=14;spacingRight=14` | `svg.py` + `export/drawio.py` |
| 2 | edges curved in draw.io, sharp in engine | **unified**: shared `edge_svg_line` rounds bends in every engine writer; draw.io `rounded=1`. **Default curved**, opt-in `theme.edgeCorners="straight"` | svg/swimlane/er/sequence + drawio + schema + compile |
| 3 | ER header poked out of rounded container | ER container → **square** corners (draw.io-native table) so the dark header aligns | `export/drawio.py` |
| 4 | no draw.io for sequence diagrams | `_emit_sequence_chrome`: dashed lifelines + activation bars; un-skipped in `build_review` | `export/drawio.py`, `tools/build_review.py` |

Tests: `tests/test_review_fixes.py` (7). win32 baselines regenerated (curved edges + cube label
churn all edge-bearing samples) — **linux/macOS baselines still need the `baselines.yml` regen**.
Full gate green; coverage 92.38%. `theme.edgeCorners` threaded through compile like `badgeCorner`.

## Review round 4 (2026-06-14) — style options on ALL writers + text fidelity

Owner reframe: visual aspects are **user style options** (honored by SVG, draw.io, and future
writers identically — controlled via spec), NOT draw.io bugs. Only *text-centric* items are pure
fidelity fixes (draw.io → match SVG).

**Style options (apply to both writers; default = SVG):**
- `theme.entityCorners` = `rounded` (default) | `square` — honored by `render/er.py` AND draw.io.
  Restored rounded ER (header shares the container radius → no poke-out artifact).
- Border/edge **width** is now read from the same spec style by both writers: draw.io node cells
  emit `strokeWidth` from `border.width`; draw.io edges use the SVG per-family default
  (swimlane 2, er/sequence 1.5) and honor `edge.style.width`. Border **color** already shared.
- (existing: `theme.edgeCorners`, `theme.badgeCorner` — both already apply to both writers.)

**Text-centric fidelity (draw.io → SVG, not options):**
- Cube label → separate text cell centred on the **front face** (draw.io's `shape=cube` centres on
  the bbox and ignores depth; spacing didn't work). `_emit_cube_label`.
- Sequence message labels → raised **above** the line (`verticalAlign=bottom`), matching the SVG.

All draw.io-only except the (default-unchanged) ER renderer → **no baseline regen**. Tests:
`tests/test_review_fixes.py` (now 13). Full gate green; coverage 92.47%.

## Review round 5 (2026-06-14) — pixel pass on engine vs draw.io

Systematic engine↔draw.io comparison (Option-A viewer) of swimlane-pipeline, er-shop,
sequence-login, deployment-web-stack, arabic-flowchart. Confirmed all round 1–4 items hold;
fixed the remaining divergences (all draw.io-only except the sequence label lift). Method: a
shape probe (`out/probe.drawio`) rendered through draw.io's viewer settled the cube/cylinder
style keys empirically before coding.

| # | Issue (owner-reported unless noted) | Root cause | Fix |
|---|---|---|---|
| 1 | cube **facing** mirrored (draw.io right, SVG left) **and** front-face label off | draw.io `shape=cube` extrudes depth top-**left**; the engine top-right | `flipH=1` on the cube cell → front face bottom-left like the SVG; the separate label cell then lands on it |
| 2 | cylinder **height** less in draw.io | `cylinder3` default cap is deep (squat look) | `shape=cylinder3;size=9` — cap == engine `ry=9` |
| 3 | sequence message label **gap** to line unequal | no shared lift | one constant: SVG `sequence._LABEL_LIFT=4` + draw.io `spacingBottom=4` (=`_SEQ_LABEL_GAP`) |
| 4 | swimlane badge **font** differs | no `fontFamily` → draw.io default ≠ SVG Cairo | `fontFamily=Cairo,sans-serif` on all text cells (sans fallback; never serif) |
| 5 (mine) | sequence diagram **title** dropped | draw.io emitted titles only for swimlanes | emit a centered title cell for sequence (engine renders titles for swimlane+sequence only) |
| 6 (mine) | plain-node label **colour** black | mxGraph default vs engine `#14281D` | default `fontColor=#14281D` in `_node_style` |
| 7 (mine) | ER PK/FK **pill** over-rounded | `arcSize=30` (30%) | `absoluteArcSize=1;arcSize=3` == SVG `rx=3` |

**Fonts ceiling (note):** draw.io can't embed fonts. `fontFamily=Cairo,sans-serif` names the
SVG's face (matches in a Cairo-equipped draw.io Desktop) and falls back to **sans** elsewhere —
the viewer (no Cairo) renders a generic sans, close to Cairo but not glyph-identical. A bare
`fontFamily=Cairo` was rejected: the viewer fell back to **serif**, worse than the default.

Tests: `tests/test_review_fixes.py` (now 20). Only SVG change = sequence label lift → win32
`sequence-login.png` baseline regenerated (others byte-identical, determinism confirmed);
**linux/macOS baselines still pending** via `baselines.yml`. Full gate green.

## Review round 6 (2026-06-14) — fill-only borders + badge font

Owner note on swimlane-pipeline: actor/user chips still showed black borders; badge digits a
different font. Both addressed (draw.io + dev-tool only — no SVG change, no baseline regen):

- **Black borders.** Every cell that is *fill-only in the SVG* (lane chips, title bar, phase
  bands, lane-group gutter, ER title, ER PK/FK pill) now sets `strokeColor=none` — mxGraph
  otherwise draws a default 1px black border. Confirmed gone in the viewer.
- **Badge / all-text font.** The .drawio already names `fontFamily=Cairo,sans-serif`; draw.io
  can't embed fonts (fonts ceiling), so the headless viewer fell back to a generic sans while
  the SVG uses embedded Cairo. `tools/verify_drawio.py` now injects the bundled Cairo `@font-face`
  into the render page, so the **review bundle reflects draw.io WITH Cairo** (as draw.io Desktop
  does once the bundled OFL Cairo is installed). Badge digits now match the SVG in the review.
  *Residual ceiling:* a draw.io install WITHOUT Cairo still falls back to sans; zero-dependency
  parity would require embedding the font in the file — done in round 7 below.

Tests: `tests/test_review_fixes.py` (now 22). Also wrapped a pre-existing >100-col line in
`tools/build_review.py` that the configured ruff scope flags. Full gate green.

## Review round 7 (2026-06-14) — embedded font + full-corpus sign-off bundle

- **Font embedding (raises the fonts ceiling none → full).** `_embed_font` puts the bundled
  Cairo subset INTO the .drawio as a single registering cell's `fontSource` (a self-contained,
  URL-encoded `data:` URI). mxGraph turns that into a global `@font-face` for `Cairo`, so every
  `fontFamily=Cairo` cell renders Cairo with **zero setup** — no install, no network. **Verified
  in the viewer with font injection OFF** (`inject_font=False`): the file renders Cairo on its
  own, across LTR, **RTL/Arabic** (shaping intact), and themed/phase diagrams. Deterministic
  (timestamp-free, codepoint-sorted subset; first-text-cell registrar) → byte-identical per spec.
  Subset is small: swimlane-pipeline .drawio ≈ 38 KB. `build_review` now renders with
  `inject_font=False` so the bundle shows the true self-contained file.
- **Full-corpus review** rebuilt for owner sign-off: all 17 `examples/*.json` →
  `out/review/index.html` (engine vs draw.io side-by-side).

Tests: `tests/test_review_fixes.py` (now 24, +embed presence +determinism). No SVG change → no
baseline regen. Full gate green.

## Review round 8 (2026-06-14) — state pseudostates + crisp chrome corners

- **State initial/final pseudostates.** They have no `_SHAPE_STYLE` entry, so draw.io drew plain
  white boxes. `_emit_pseudostate` now renders them as ellipses matching `render/svg.py`: initial =
  a solid dot filled with the stroke colour; final = a bullseye (outer ring + inner dot). Verified
  on `state-order-lifecycle`.
- **Crisp corner radius (owner-preferred style → new default, both writers).** Phase bands and
  nested-lane group gutters used a softer 5–6px (SVG) / percentage `arcSize` (draw.io). Now a
  shared crisp `_CHROME_RADIUS=3` absolute in both (`swimlane.py` rx, draw.io `absoluteArcSize`).
  SVG-default change → win32 baselines regenerated: `swimlane-phases.png`,
  `swimlane-nested-delivery.png` (others byte-identical / sub-tolerance). **linux/macOS pending.**

Tests: `tests/test_review_fixes.py` (now 26). Full gate green.

## Review round 9 (2026-06-14) — tighter edge-label halo

Owner (state-order-lifecycle "deliver"): the white box behind edge labels is too much; draw.io
(no box) is cleaner. The SVG halo was an oversized 18px-tall / `len*3.5*2`-wide box (text is
`dominant-baseline=central`, so ~3px of slab on every side, crowding the adjacent bullseye).
Shared `_edge_label_bg` now hugs the text (`height=15`, `half=max(7,len*3+1)`, opacity 0.85) and
is reused by the generic, swimlane, and ER writers (was three near-duplicate inline boxes).

SVG-default change → 12 win32 baselines regenerated (every edge-labelled sample). **linux/macOS
pending.** Tests: `tests/test_review_fixes.py` (now 27). Full gate green.

## PPTX writer (2026-06-14) — native shapes, branch `phase-6-pptx`

`src/tarseem/export/pptx.py`: python-pptx **native** autoshapes + freeform connectors + text from
the positioned IR (invariant 5 — no image, no SVG ungroup). IR px → EMU (9525/px); slide margin
matches the SVG framing per family (generic/ER +24px, swimlane/sequence absolute). Edges are
freeform polylines with an XML-patched `a:tailEnd` arrowhead; RTL labels get `a:pPr rtl="1"`
(no python-pptx API). All families covered: shape vocab + state pseudostates, swimlane chrome
(bands/chips/title/phases/groups/separators), sequence lifelines+activations, ER table cells,
markers, badges. Wired into `engine.export(["pptx"])` + `.report.json` sidecars.

**Determinism (invariant 7):** a .pptx is a zip python-pptx stamps with wall-clock mtimes +
core-prop timestamps. Core props pinned to a constant; the zip is re-emitted with normalized
`ZipInfo` → byte-identical per spec (tested across 7 families).

**Verification:** structure/determinism/EMU-scaling/RTL/report tested (`tests/test_export_pptx.py`,
20 tests). No headless PPTX renderer exists, so on-canvas appearance is an owner step — decks at
`out/pptx/*.pptx`, checklist at `docs/pptx-manual-checklist.md`.

| Feature | Level | Notes |
|---|---|---|
| shapes | full* | rect/roundrect/stadium/diamond/parallelogram/can/document/cube + state dot/bullseye. *unknown → rect + warning |
| lanes / phases | full | explicit rects + chips + phase bands (matches the SVG/ADR-007 chrome) |
| badges / markers | full | corner-circle ovals; start dot + end bullseye |
| edge_routes | full | exact IR polyline as a freeform connector (floating, not shape-bound) |
| edge_labels | full | textbox with a tight white halo |
| curved_edges | none | straight segments only |
| ports | partial | ER rows are explicit cells, not native table ports |
| gradients | none | flat fills |
| fonts_embedded | none | names Cairo (`a:cs` too); **install Cairo to render** (verified). Not embedded — embedding deferred (PowerPoint repair). |
| rtl_shaping | partial | `a:pPr rtl=1`; shaping delegated to PowerPoint |
| theme_fidelity | partial | flat fills/strokes/text colours; no gradients/tints |
| metadata | full | provenance in core properties (no wall-clock) |

## PPTX review round 1 (2026-06-14) — owner PowerPoint pass (17 decks)

Fixes from the owner's first real-PowerPoint review:

- **Edge-label background → transparent** (global, incl. the SVG source of truth + PPTX; draw.io
  already none). The white halo read as a white gap in the line ("some links are white"). Removed
  the slab in `svg.py`/`swimlane.py`/`er.py` (deleted `_edge_label_bg`); PPTX label textboxes have
  no fill and don't wrap (`word_wrap=False`) → fixes sequence labels spilling to two rows.
- **Curved edges (PPTX)** — freeform now traces rounded corners (quadratic sampled into segments,
  `_EDGE_RADIUS=8` matching the SVG), honoring `theme.edgeCorners`.
- **Arabic font (PPTX)** — set `a:cs`/`a:ea` typeface to Cairo (python-pptx only sets `a:latin`,
  so Arabic was falling back to the theme's complex-script font).
- **Blurry separators (PPTX)** — straight separators/lifelines/ER row rules now use **connectors**
  (`p:cxnSp`), not degenerate zero-width freeforms.
- **ER title corners (PPTX)** — title is a rounded rect so its top follows the container.
- **Vertical gutter text (PPTX)** — nested-lane group label gets `bodyPr vert="vert270"`.
- **3-D drop shadow** (owner liked it) — added to cube + cylinder in **all** writers: SVG
  (`feDropShadow` filter), draw.io (`shadow=1`), PPTX (`a:outerShdw`).

SVG-default changes (edge-label slab + shadow) → 12 win32 baselines regenerated; **linux/macOS
pending** (CI at PR time). Tests: `tests/test_export_pptx.py` (24), `tests/test_review_fixes.py`
(+SVG slab/shadow). Full gate green. **Arabic/English mixed-bidi spacing (review #3): confirmed
working in PowerPoint by the owner (2026-06-15)** — `rtl` + per-run `lang` + complex-script Cairo
font produce correct mixed Arabic/Latin spacing. PPTX manual PowerPoint close-out complete.

## PPTX review round 2 (2026-06-14) — labels off the line + rounded-by-default

- **Edge labels off the line (all writers).** New post-layout transform `offset_edge_labels`
  (`model/edge_labels.py`, run in `engine.render`) nudges each `label_xy` perpendicular off its
  nearest segment — above a horizontal segment, beside a vertical one (right LTR / left RTL) — so
  the line never passes through the text. SVG/PPTX read the corrected point; draw.io now emits the
  label as a **separate text cell** at `label_xy` (it otherwise centres an edge value on the line).
  Removed the per-writer label hacks (`_LABEL_LIFT`, `verticalAlign=bottom`/`spacingBottom`,
  pptx `label_above`). Idempotent (offset measured from the line).
- **Rounded corners by default (all writers, all types).** `theme.nodeCorners` (new schema enum,
  default `rounded`); `compile` maps `rect → roundrect` so every writer renders rounded with no
  writer change. Opt out globally with `nodeCorners="sharp"`.
- **PPTX ER title** → `ROUND_2_SAME_RECTANGLE` (rounded top, square bottom — matches the SVG;
  the plain rounded rect rounded the bottom too).
- **PPTX Arabic mixed (review #2)** — set each run's `lang` (+ existing `rtl`/`cs` font) so
  PowerPoint applies bidi; **single-run only — mixed Arabic/Latin spacing may still need
  per-script run-splitting (unverifiable without PowerPoint; flagged for re-check).**

SVG-default changes (rounded rects + label positions) → all 13 win32 baselines regenerated;
linux/macOS at PR time. Tests updated. Full gate green.

**Review bundle reorganized (owner request):** `tools/build_review.py` now writes one folder per
format — `out/{svg,png,drawio,pptx}/` — plus a single `out/index.html` (every diagram across every
format, side by side; PPTX as a download tile since it has no headless render) and a generated
`out/README.md`. Locked files (an open `.pptx`/`.drawio`) are skipped with a `[locked]` log.
`out/index.html` is the one sign-off surface.

## PPTX review round 3 (2026-06-14)

- **PPTX Arabic font (#2) — RESOLVED via font install.** The decks name `Cairo` in the
  complex-script slot (`a:cs`); **with Cairo installed, PowerPoint renders Latin + Arabic correctly
  (owner-confirmed).** Fonts are not embedded (ceiling = `none`): a plain OPC embed was structurally
  valid + deterministic + reopened in python-pptx, but **PowerPoint flagged the file for repair**, so
  it was reverted. Zero-install embedding → **deferred future task** (below).
- **Sequence actors rounded (#3).** `SequenceLayout` hardcoded `shape="rect"` for participant
  heads, ignoring the compiled (rounded) shape — now uses `n.shape`, so `nodeCorners` applies.
- **Cylinder label centring (#4).** SVG/draw.io centred the label on the bbox; now dropped onto
  the body below the top cap (`_CYL_CAP`; draw.io `spacingTop`) to match PPTX's CAN. swimlane now
  uses the shared `_label_center`.
- **PPTX ER header (#1).** The container's default rounded-rect radius was large; pinned both the
  container and the `ROUND_2_SAME_RECTANGLE` title to ~6px so the title's rounded top aligns with
  the container (no poke-out).

SVG-default changes (rounded sequence heads + cylinder label) → win32 baselines regenerated;
linux/macOS at PR time. Tests added. Full gate green.

## PDF writer (2026-06-14) — Chromium print, branch `phase-6-pptx`

`src/tarseem/export/pdf.py`: a thin Chromium print-to-PDF of the **canonical SVG** (mirrors
`png.py`). Like PNG it renders the source-of-truth SVG, so it drops nothing relative to the SVG
and carries **no CapabilityReport** (a faithful render has nothing to report; PNG is the same —
note: the earlier PPTX-track option text mentioned a PDF report, deliberately dropped after
review as it would be all-`full` ceremony — if uniform per-format reports are wanted, the
consistent fix is reports for png **and** pdf, not pdf alone). Wired into `engine.export(["pdf"])`
+ the CLI + the review bundle (`out/pdf/`, previews inline in `index.html`).

The two parts of "mirror png.py" that do **not** transfer (a PDF is a paginated document, not a
bitmap), both handled + tested:
- **Page sizing.** `page.pdf` paginates; an inline `<svg>` adds a line-box descender that spills a
  hairline 2nd page. Fixed with `svg{display:block}` + `ceil`'d page dims (no clip on fractional
  extents). Asserted single-page on a **tall** (sequence) and **wide** (vertical swimlane) sample.
- **Determinism (invariant 7).** Chromium stamps the Info dict with wall-clock `/CreationDate` +
  `/ModDate` (14-digit, fixed-length, plaintext; **no `/ID`**). `_normalize_pdf_dates` overwrites
  the digits with a constant of equal length → byte offsets (and the xref) untouched, no PDF dep.
  A determinism test is load-bearing: a future Chromium that changes the date format / adds `/ID` /
  moves dates into a compressed stream fails loudly.

**Fidelity ceiling (visually verified here by rendering the PDF vs the canonical PNG — the Read
tool renders PDFs; no separate headless PDF renderer needed):**

| Aspect | Level | Note |
|---|---|---|
| visual fidelity | full | shapes/lanes/badges/markers/edges/colors match the SVG; **Arabic shaped + joined + RTL correctly** |
| fonts | self-contained | Skia carries Cairo glyphs as **Type3 vector procedures** (renders with zero fonts installed) — not a TrueType embed |
| text layer | partial | extractable/searchable text is clean for Latin but **garbled for Arabic** (Type3 has no reliable Unicode); the *picture* is correct. A searchable-Arabic layer was investigated and **deferred** — see "Searchable/selectable Arabic in PDF" below |
| raster | minor | some compositing (e.g. semi-transparent lane fills) flattens to a small `/Image` — **not visible** at the rendered size |
| metadata | none | provenance not embedded yet (PDF XMP = sub-stage 5, "where practical") |
| determinism | full | same spec ⇒ byte-identical (dates pinned) |

## Deferred / future tasks

- **Mermaid + PlantUML source writers (deferred 2026-06-15 → future feature).** Sub-stage 4 —
  best-effort DSL source exports from the **logical IR** (`result.graph`) with CapabilityReports, per
  `08-export-strategy.md` (best-effort tier) and FR-11.7/FR-11.8. **Dropped from the initial Phase-6
  delivery** and recorded as a future feature; the design is unchanged (lossy, capability-reported
  writers — lanes→subgraph approximation, ports dropped, Arabic diacritics quoted/stripped with a
  warning per R-6). Synced: `11-phased-plan.md` (Phase 6 scope), `12-acceptance-criteria.md` (F7),
  `01-requirements.md` (FR-11.7/11.8). The IR-retention comments in `engine.py`/`export/__init__.py`
  stay valid (they exist precisely so these future writers can traverse the pre-layout graph).

- **Searchable/selectable Arabic in PDF (deferred 2026-06-15, owner-approved).** Chromium prints
  shaped Arabic as Type3 visual-order glyphs with no logical Unicode, so the committed `8098cc1` PDF
  is visually perfect but Arabic isn't searchable. A full investigation (**`spikes/spike-5-pdf-searchable/`**,
  report **`docs/spikes/spike-5-report.md`**) validated an invisible Type3+ToUnicode "OCR-sandwich"
  layer over a `textAsPaths` base, Tagged PDF + `/ActualText`, deterministic, with a CTM-isolation fix
  (`q … Q`) — it yields **selectable text + single-word Ctrl+F search** in Acrobat, but **multi-word
  phrase search does not work** (Acrobat indexes shown-glyph ToUnicode, not `/ActualText`, and rejects
  a synthetic RTL layout; four glyph layouts tried, none reliable; no headless Acrobat oracle). Owner
  decision: keep the visual-only PDF. **Spike-only deps (`pikepdf`, `pdfminer.six`) are NOT in
  `pyproject.toml` — production is unchanged.** If revisited: true per-glyph shaper positions
  (uharfbuzz) + iterative Acrobat validation.

- **PPTX zero-install font embedding (Arabic/Cairo).** Goal: embed Cairo in the `.pptx` so it
  renders without installing the font (raise the PPTX fonts ceiling `none → full`, as done for SVG
  + draw.io). A plain OPC embed (font part + `embeddedFontLst` + `embedTrueTypeFonts`) was
  structurally valid and reopened in python-pptx, but **real PowerPoint flagged the file for
  repair** → reverted (commit `8c80c01`). Likely needs PowerPoint's **font obfuscation** (the
  `.fntdata` XOR-masked by the embed GUID) and/or a different `embeddedFontLst` placement.
  **Must be done as an iterative loop with PowerPoint to validate after each attempt** — no
  headless PPTX renderer exists here, so it can't be verified blind. Until then: install Cairo
  (verified working). Owner-approved to pursue later.

## Fidelity ceiling — draw.io (Option-A + Option-B verified ✅)

✅ **Option A** (draw.io viewer / mxGraph) **and ✅ Option B** (draw.io **Desktop** engine,
headless via Docker `rlespinasse/drawio-desktop-headless`) **both render all 6 samples matching
the canonical SVG.** Desktop confirmed the viewer on the RTL swimlane (header chips right), the
phases/LTR swimlane (title bar + phase bands + left chips), and the shape vocabulary. Confirmed
keys: `shape=rhombus`, `shape=cylinder3`, `shape=cube`, `shape=parallelogram`, `shape=document`,
`rounded=1;arcSize=50`, `edgeStyle=none`+waypoints (exact polyline). Lane chrome is explicit
cells (ADR-007), so header side + phase bands match in both engines.

Reported per export against the shared vocabulary; `none`/`partial` always emit a machine
warning into the `.report.json` sidecar (never a silent drop).

| Feature | Level | Ceiling / why |
|---|---|---|
| shapes | full* | rect/roundrect/stadium/diamond/parallelogram/cylinder/document/cube mapped to documented mxGraph keys. *Unknown shape → plain box + warning. |
| lanes | full* | **ADR-007**: explicit rects + header chips matching the SVG (RTL chips flip to the right); nested-lane gutters drawn. *Static rects, not draggable swimlane containers (`editability-limited` warning). |
| phases | full | **ADR-007**: phase header bands + dashed separators drawn (previously dropped). |
| badges | partial | no native badge cell — auto-number folded into the node label text. |
| markers | full | UML start/end → ellipse cells. |
| edge_routes | full | exact IR polyline via `sourcePoint`/`targetPoint` + interior `mxPoint` array under `edgeStyle=none`. Edges are **floating, not node-bound** (IR has no edge→node identity; binding would let draw.io re-route and discard the exact points) — geometry is exact, live node-reconnection is traded away. |
| edge_labels | full | edge `value`. |
| curved_edges | none | orthogonal only. |
| ports | none | ER attribute rows folded into entity label (no native table ports). |
| gradients | none | flat fills only. |
| fonts_embedded | full | bundled Cairo subset embedded via a single `fontSource` data: URI (one registrar cell, global `@font-face`); renders in Cairo with zero setup (round 7). |
| rtl_shaping | partial | `writingDirection=rtl` set; bidi shaping delegated to diagrams.net's renderer. |
| theme_fidelity | partial | fill/stroke/font colours + lane hue carried; tints approximate, no gradients. |
| metadata | full | provenance as an XML file comment. |

## Style-key subset (R-14) — documented keys only, pending round-trip confirmation

Only keys believed documented in mxGraph are emitted (confirm on first round-trip): `swimlane`,
`rounded`, `arcSize`, `rhombus`,
`shape=parallelogram`, `perimeter=parallelogramPerimeter`, `shape=cylinder3`, `shape=document`,
`shape=cube`, `ellipse`, `html`, `whiteSpace`, `fillColor`, `strokeColor`, `fontColor`,
`startSize`, `horizontal`, `edgeStyle=orthogonalEdgeStyle`, `dashed`, `writingDirection`,
`align`. No guessed/undocumented keys.

## Resume checklist

1. Re-anchor: CLAUDE.md + `git log --oneline -8` + Phase 6 in `11-phased-plan.md` + `.venv` pytest.
2. Writer contract is set: `write_<fmt>(diagram_or_graph, out_path, meta) -> WriteResult(path, report)`;
   wire new formats into `RenderResult._export_writer` + the `export()` dispatch.
3. PPTX next (shares positioned-IR geometry with drawio; python-pptx already a core dep — lazy-import
   like `png.py`). Then PDF (trivial, mirror `png.py`). **Mermaid/PlantUML deferred to a future
   feature** (logical-IR source writers — see "Deferred / future tasks"). class+mindmap is a separate
   family/layout workstream — land last.
4. No phase ships with red CI; nothing reaches `main` without a PR; new examples take the baseline cost knowingly.
