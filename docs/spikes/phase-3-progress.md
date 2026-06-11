# Phase 3 — Browser Gallery & Test Harness (progress + MVP audit)

Goal (11-phased-plan §Phase 3): verification infrastructure + the first non-graph family,
then **MVP declared** when A6–A10 are green on the matrix. Work order this phase:
A10 → RenderReport → phases(FR-6.3) → gallery(A6/A9) → screenshot tooling → E2E(A6) →
3-OS CI(A7/A8) → prove regression → audit.

## Phase-3 deliverables

| Deliverable | Status | Tests / artifact | Notes |
|---|---|---|---|
| A10 sequence layouter + profile | ✅ green | `tests/test_a10_sequence.py` (11); `phase-2-goldens/sequence-login.{svg,png}` | pure-Python deterministic layouter (lifelines=columns, messages=time-rows, activation bars from call/return nesting, self-message brackets); reuses the one positioned IR (heads→nodes, messages→edges, new `Activation` overlay) |
| RenderReport metrics | ✅ green | `tests/test_render_report.py` (9) | crossings (proper-intersection, shared-endpoint excluded), node overlaps, extent, engine-injected timing; `RenderResult.report`; surfaced per-sample in the gallery |
| Phase-grouping columns (FR-6.3) | ✅ green | `tests/test_phases.py` (8); `phase-2-goldens/swimlane-phases.{svg,png}` | phase header bands span member columns, dotted separators drop through lanes, lanes shift down; IR `LogicalPhase`/`PhaseBand` |
| Gallery builder (A6/A9) | ✅ green | `tests/test_gallery.py` (6); `tarseem gallery` | static index (inline-SVG thumbnails, Chromium-free build) + detail pages (inline SVG, metrics, spec JSON, downloads); failed sample recorded not dropped |
| Screenshot baselines + pixel diff | ✅ green | `tests/test_visual_regression.py` (5 unit + 4 baseline); `src/tarseem/visualtest.py`; `tests/baselines/win32/` | pixelmatch-style `compare_png` (tolerance + ratio gate + diff image); `scripts/regen_baselines.py` |
| Playwright E2E (A6) | ✅ green | `tests/test_e2e_gallery.py` (2) | real Chromium: index + every detail page load error-free with inline SVG and resolvable downloads |
| 3-OS CI matrix (A7/A8) | ✅ all 6 jobs green | `.github/workflows/ci.yml`; run #27332733033 | ubuntu/windows/macos × py3.10/3.12; installs Chromium; ruff/mypy/doctor/pytest/gallery; uploads gallery artifact. Windows legs ran the pixel-baseline comparison and passed (CI Chromium matched committed win32 baselines within the 0.1% gate) |
| Prove visual regression | ✅ demonstrated | see below | deliberate 2px head-border change → gate fails at 0.551% (caught); revert → green |

Full suite **122 passed**; ruff + mypy clean.

## Visual-regression proof (R-21 harness validation)

On a throwaway branch, the sequence head border width was changed 2→4 px (a 2px style
change). The baseline gate failed precisely:

```
FAILED tests/test_visual_regression.py::test_render_matches_baseline[sequence-login]
  sequence-login: 8448/1532160 px changed (0.551%) vs baseline; review …/sequence-login.diff.png
  assert 0.00551 <= 0.001
```

The diff image highlighted exactly the four participant-head borders; the other three
baselines (unaffected) stayed green. The change was reverted. This exposed that the initial
1% gate was too loose (0.551% would have slipped through), so the gate was tightened to
**0.1%** with tolerance 8 — tight enough to catch a 2px change, loose enough to ignore the
sub-pixel anti-aliasing drift that can appear between Chromium builds.

## Baseline policy (09 §1, R-21)

- Baselines live under `tests/baselines/<sys.platform>/`; the comparison runs only where a
  baseline exists for the current platform and **skips** elsewhere with a clear reason.
- Regeneration is explicit and reviewed: `python scripts/regen_baselines.py`. The PNG churn
  is reviewed in the PR — baselines never auto-update.
- Only the deterministic, Node-free families are baselined, keeping the regression suite
  hermetic (no ELK subprocess).

## CI / per-OS path (A8)

`.github/workflows/ci.yml` runs the full pipeline on ubuntu/windows/macos × py3.10/3.12:
install → Chromium → ruff → mypy → `tarseem doctor` → pytest (schema/unit/render/E2E/visual)
→ gallery build → wheel/sdist → gallery artifact upload. The visual-regression layer is
active on the platform whose baselines are committed (currently win32) and skipped on the
others until their baselines are added.

---

# MVP Acceptance Audit (A1–A12)

Each criterion with its verifying test/artifact, and an honest verification-strength call.

| # | Criterion | Verifying test / artifact | Strength |
|---|---|---|---|
| A1 | Validated specs accepted; invalid rejected with coded, path-precise errors | `tests/test_a1_validation.py` (13); `schema/core.py` + `validation/` | **Strong** |
| A2 | Flowchart / architecture-C4 / dependency via ELK | `tests/test_a2_render.py` (10); goldens `phase-2-goldens/{flowchart,architecture,dependency}.{svg,png}` | **Strong** |
| A3 | SVG + PNG deterministic across runs | `tests/test_a3_determinism.py` (5) — cross-hash-seed + cross-time | **Strong** |
| A4 | Clean Python API + CLI equivalents | `tests/test_a4_api.py` (11); `engine.py`, `cli/` | **Strong** |
| A5 | Styling: theme + overrides + named presets | `tests/test_a5_styling.py` (9); golden via A2 | **Strong** |
| A6 | Gallery builds; all samples render error-free in Chromium | `tests/test_gallery.py` (6) + `tests/test_e2e_gallery.py` (2) | **Strong** |
| A7 | Automated tests at schema/unit/contract/render/E2E in CI | all `tests/`; `ci.yml`; `tests/test_adapter_contract.py` (6) | **Strong** — ⚠1 resolved (unified adapter-contract suite + 80% coverage gate) |
| A8 | Green on ≥1 OS + documented path for Win/macOS/Linux | `ci.yml` 3-OS matrix — all 6 jobs green; baselines for win32/linux/darwin | **Strong** — ⚠2 resolved (visual regression now runs on all 3 OS) |
| A9 | Documented examples for every MVP family (gallery = docs fixtures) | `examples/` + gallery + `docs/guide/`; `tests/test_docs.py` (4) | **Strong** — ⚠3 resolved (prose quickstart + family guide, doc-rot test) |
| A10 | Sequence diagrams via deterministic layouter | `tests/test_a10_sequence.py` (11); golden | **Strong** |
| A11 | `engine doctor` verifies Node/elkjs/Playwright/fonts | `tests/test_a11_doctor.py` (9) | **Strong** |
| A12 | Swimlane LTR: reference shapes/markers/back-edges; Ref-1 & Ref-3 reproduced | `tests/test_a12_swimlane.py` (16) + `tests/test_phases.py` (8) + `tests/test_reference_contract.py` (2); goldens | **Strong** — ⚠4 resolved (reference-fidelity contract encoded) |

## Soft spots — all four resolved (post-audit)

The four ⚠ items flagged below were subsequently fixed; each entry keeps the original
honest assessment followed by **Resolved:** with the fix. Full suite now **134 passed**,
coverage 92.67% (gate 80%), matrix green on all 3 OS.

## Honestly weakly verified (original audit)

**⚠1 — A7 "contract" layer is implicit, and there is no coverage gate.** The plan calls for
an adapter-contract suite where *every* `LayoutAdapter` (ELK, lane-grid, sequence) passes
the *same* parametrized invariants (positions present, ports respected, partitions
monotonic, determinism). Today those checks are spread across per-family tests, not a single
contract suite — so a new adapter could be added without being forced through the shared
contract. Also `testing.md` asks for 80% coverage; no `--cov-fail-under` gate is enforced.
*Fix:* add `tests/test_adapter_contract.py` parametrized over all adapters; add a coverage
gate. (Low effort, real value.)
**Resolved** (`bf4bd67`): `tests/test_adapter_contract.py` parametrizes one contract over
ELK/lane-grid/sequence (positive extent, finite/positive node geometry, finite edge points,
determinism, no ELK-JSON leak); CI enforces `--cov-fail-under=80` (current 92.67%).

**⚠2 — Screenshot regression is single-OS.** All 6 matrix jobs are green, and the Windows
legs *did* run the pixel comparison against the committed win32 baselines and passed — so the
baselines are stable cross-machine, not just on my box. But the *pixel* comparison still only
runs where baselines exist (win32); macOS/Linux skip it. So visual regression is genuinely
verified on one OS only; cross-OS font rasterization is unguarded until per-OS baselines are
generated on their runners. *Fix:* run `regen_baselines.py` on linux/macos CI legs (or a
matrix job) and commit those baselines.
**Resolved** (`9f9287b`): added `.github/workflows/baselines.yml`; ran it on real runners
(#27350355859) and committed `tests/baselines/{linux,darwin}/`. The pixel comparison now
runs on all three OS instead of skipping linux/macos.

**⚠3 — A9 "documented" = the gallery, not prose.** Every MVP family has a golden example and
a gallery page, which satisfies "gallery = docs fixtures". But there is no user-facing
quickstart/guide yet (those are scheduled for later phases). If A9 is read as "prose docs per
family", it is not met; if read as "a rendered, inspectable example per family", it is.
**Resolved** (`380a1ec`): `docs/guide/quickstart.md` + `docs/guide/families.md` document
every family with a minimal spec; `tests/test_docs.py` guards against doc rot (every
referenced example exists, every example + diagramType is documented).

**⚠4 — A12 reference fidelity is eyeball, not automated.** Ref-1/Ref-3 reproduction was
confirmed by visual side-by-side (and looks faithful), but there is no automated comparison
of the rendered swimlanes against the reference PNGs in `references/`. The *mechanics*
(lanes, pills, hues, badges, shape set, markers, back-edges, phases) are unit-tested; the
*visual match* to the references is manual.
**Resolved** (`07725d7`): `tests/test_reference_contract.py` encodes the analysis.md visual
contract for Ref-1/Ref-3 as assertions (lane set, reference shape set, UML markers, numbered
badges with terminals exempt, hue tints, title bar, geometric back-edge detection). Pixel
identity to the draw.io references stays intentionally out of scope (different renderer).

## Net

**All twelve criteria are now strongly verified.** The four post-audit fixes closed the soft
spots: A7 has a unified adapter-contract suite + coverage gate, A8's visual regression runs on
all three OS, A9 has prose docs with a doc-rot test, and A12 has an automated reference-fidelity
contract. The matrix is green on Windows/macOS/Linux × py3.10/3.12; full suite 134 passed,
coverage 92.67%. The only remaining intentional non-goal is pixel-identity to the draw.io
reference exports (different renderer — contract fidelity is the gate instead).
