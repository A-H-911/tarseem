# Phase 4 — Styling, Themes & Arabic/RTL — progress

Governing docs: `docs/plan/11-phased-plan.md` (Phase 4), `docs/plan/07-rtl-arabic-strategy.md`,
`docs/plan/references/analysis.md` (§Reference-2 gate). Decisions: **Cairo-only** font scope;
themes **default + corporate + monochrome** (D10 confirmed; Noto/IBM-Plex deferred).

## Deliverables

| Deliverable | Status | Where |
|---|---|---|
| 6-level style cascade | ✅ verified (already present) | `themes/cascade.py`; `theme.ref`\|`name` fix in `model/compile.py` |
| RTL-aware built-in themes | ✅ default/corporate/monochrome | `themes/__init__.py`; palette now sourced from theme (F4) |
| Cairo bundling / subset / data-URI embed | ✅ (already present) | `render/fonts.py` |
| Arabic measurement (uharfbuzz primary) | ✅ | `measure/`; test `test_arabic_rtl.py` |
| raqm cross-check (best-effort) | ✅ informational; skipped w/o libraqm | `doctor.check_raqm`; `test_raqm_cross_check…` |
| doctor Arabic-shaping gate | ✅ | `doctor.check_arabic_shaping` |
| Bidi base-direction resolution (auto-detect) | ✅ | `render/text.py`; wired into all 3 writers |
| RL mirroring end-to-end | ✅ ELK flow + swimlane header/badge/separator/markers | `layout/elk`, `layout/lanegrid`, `render/swimlane.py` |
| `textAsPaths` export option | ✅ uharfbuzz shape → fontTools outlines | `render/textpath.py`, `render/export_opts.py` |
| `embedFonts` toggle | ✅ | `render/export_opts.py`; schema `export.svg` |
| Arabic golden suite | ✅ 4 examples | `examples/{swimlane-document-rtl,arabic-flowchart,arabic-architecture,arabic-mixed}.json` |
| Reference-2 rebuild | ✅ side-by-side reviewed | `examples/swimlane-document-rtl.json` |
| `rtl-arabic.md` guide | ✅ | `docs/guide/rtl-arabic.md` |
| Arabic/RTL gallery presence | ✅ auto-included (family-tagged cards) | `examples/*.json` → gallery |

## Bans honoured

- **No CairoSVG** anywhere (raster path is Playwright/Chromium only).
- **No pre-shaping into the IR**: text stored logical-order Unicode; shaping happens at
  render (Chromium HarfBuzz) and in `textAsPaths` (uharfbuzz→outlines), never upstream.
- ELK JSON stays inside the layout adapter; pinned elkjs/Chromium.

## Gate status

- **Reference-2 + Arabic suite pixel-stable**: ✅ on **win32** (baselines committed). The
  LTR baselines were re-rendered and are **byte-identical** (no churn), confirming the RTL
  refactor is additive.
- **3-OS matrix**: ✅ **complete**. linux + macOS baselines were generated on the real CI
  runners via `.github/workflows/baselines.yml` and committed in `d825e5e` (merged in PR #2,
  `507574a`). All three OS dirs now hold 8 baselines each — incl. the 4 Arabic samples
  (`arabic-flowchart`, `arabic-architecture`, `arabic-mixed`, `swimlane-document-rtl`) per OS.
  The LTR baselines stayed byte-identical across the refactor (no churn).
- Native-speaker review of the Arabic samples: **requested** (owner).

## Known limitation (surfaced, not hidden)

Long lane titles do not wrap inside the fixed-width header column yet — documented in
`docs/guide/rtl-arabic.md`; automatic wrapping is a later-phase layout feature.
