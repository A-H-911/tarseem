# Testing & Browser-Gallery Strategy

Status: Proposed · 2026-06-11

---

## 1. Test Pyramid

| Level | Scope | Tooling | Phase |
|---|---|---|---|
| Schema | valid/invalid spec corpus per profile; error path/code assertions; version migration cases | pytest + jsonschema | P2 |
| Unit | style cascade resolution, measurement service (incl. Arabic strings), IR builders, hint mapping | pytest | P2 |
| Adapter contract | every LayoutAdapter passes the same suite (positions present, ports respected, partitions monotonic, determinism: two runs identical) | pytest, parametrized | P2–3 |
| Rendering | SVG structure assertions (XPath: lane bands, direction attrs, marker refs), golden SVG diffs (deterministic output makes text diff viable) | pytest + lxml | P2–3 |
| Export | drawio: schema-valid XML + draw.io CLI headless open/export probe; PPTX: python-pptx re-read + XML assertions (`rtl="1"`, geometry); PDF: text extraction sanity | pytest (+Docker drawio CLI in CI) | P6 |
| Visual regression | Chromium screenshots vs baselines; pixel diff + SSIM threshold; per-OS baselines if font deltas demand | Playwright + pixelmatch-style diff | P3 |
| Browser E2E | gallery loads, every sample renders without console errors, RTL pages `dir` correct, download links resolve | Playwright | P3 |
| Regression/perf | crossing/overlap counts tracked per golden sample (RenderReport metrics); render-time budget asserts (NFR-2) | pytest | P3+ |

Determinism is the enabler: pinned elkjs/Chromium versions (R-21); baseline regeneration is an explicit reviewed PR (`make regen-baselines`).

## 2. Sample Gallery (Layer 9)

- `examples/` = golden spec corpus: per family × {minimal, full-featured, Arabic/RTL, stress (≥100 nodes)}; every supported diagram type represented (Full criterion).
- `engine gallery build` → static HTML: index grid (thumbnail PNG, family, tags, RTL badge) → detail page (inline SVG, spec JSON, RenderReport, export downloads). No server required; openable from disk; CI publishes as artifact (and optionally GitHub Pages).
- Gallery = shared fixture for: manual visual verification (brief requirement), E2E suite, screenshot regression, documentation examples — one corpus, four consumers.

## 3. CI Matrix (Phase 3 onward)

- GitHub Actions: ubuntu + windows + macos × supported Pythons (3.10/3.12 bounds).
- Steps: install extras → `engine doctor` (verifies Node, elkjs bundle, Playwright browsers, bundled fonts, optional raqm) → unit/schema → layout contract → render goldens → gallery build → E2E + screenshots → export probes (drawio CLI via Docker on linux only; PPTX assertions everywhere).
- Artifacts on failure: diff images, RenderReports, gallery bundle.

## 4. Verification Beyond CI

- Phase-gate manual checklists (e.g., P6: open PPTX in real PowerPoint, edit a lane, confirm RTL caret behavior; P5: enterprise swimlane side-by-side with reference images).
- `engine doctor` doubles as user-support tool (R-20).
