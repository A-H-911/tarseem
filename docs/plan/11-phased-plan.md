# Phased Implementation Plan

Status: **Approved with decisions D1–D12 (2026-06-11)** — replanned for D3:B (swimlane in MVP) and D2:C (parallel editable writers). Awaiting go for Phase 0 spikes.
Each phase: goal / scope / deliverables / validation / risks / exit criteria.

---

## Phase 0 — Discovery & Validation (partially complete)

**Goal**: de-risk the four make-or-break assumptions before architecture freeze.
**Done by this mission**: project inspection (empty repo; reference images missing — D9), engine research, feasibility matrix, risk register.
**Remaining scope — 4 spikes (timeboxed, throwaway code):**
1. elkjs round-trip: Python ↔ Node subprocess, 50-node compound graph with ports, warm-call latency measured.
2. Arabic pipeline: uharfbuzz measurement → SVG with direction attrs + embedded Cairo font → Playwright PNG; verify shaping/sizing on Win+Linux.
3. Swimlane (**now MVP-gating per D3:B**): the 3 provided reference diagrams (`references/analysis.md`) rebuilt as specs via ELK partitioning; assess against §4 acceptance in `06-layout-routing-strategy.md`; decide partitioning vs. lane-grid fallback here. Mine the local `horizontal-swimlane-diagram` skill (draw.io-based prior art matching the references) for geometry/style constants.
4. Editable: hand-built drawio XML (pool/2 lanes/RTL label) opens correctly in diagrams.net; minimal python-pptx shapes+connector+`rtl="1"` deck opens in PowerPoint.
**Validation**: spike reports with screenshots appended to this repo.
**Risks**: spike failure → fallback decisions (Graphviz core / lane-grid layouter / drop a writer) per `02-risks.md`. Spike 3 failure no longer just re-plans a phase — it re-scopes MVP.
**Exit**: all four spikes pass or fallbacks chosen. (D1/D3/D9 ✅ decided 2026-06-11.)

## Phase 1 — Requirements & Architecture Baseline

**Goal**: frozen baseline to build against.
**Scope**: finalize requirements (this doc set + decisions), ADR-001…005, MVP scope lock, repo scaffolding decision (name, packaging, license — D8), CI skeleton.
**Deliverables**: approved `01/04/05` docs v1.0; ADRs; empty package + CI bootstrap.
**Validation**: stakeholder (your) sign-off.
**Risks**: scope creep — mitigated by acceptance criteria lock.
**Exit**: tagged `baseline-1.0`; build authorized.

## Phase 2 — Minimal Schema & Core Engine (MVP core)

**Goal**: JSON spec → validated → laid out → SVG/PNG, for 4 families (incl. swimlane per D3:B).
**Scope**: core schema v0 (nodes/edges/groups/**lanes/phases**/labels/styles/layout hints); validation layers 1–3; logical+positioned IR; measurement service (Latin path + Arabic-ready API); ElkLayout adapter (subprocess mgr, pinned bundle) using the spike-selected swimlane path (partitioning or lane-grid); SVG renderer — shape set sized to the references: rect/rounded/stadium/diamond/parallelogram/cylinder/document + UML start/end markers, arrowheads, edge labels, dashed edges, **lane bands + header pills + title bar + auto-number badges**, per-lane hue→tints theme function; PNG via Playwright; basic theme + cascade; CLI (`validate/render/export/doctor/examples`); flowchart + architecture/C4 + dependency + **swimlane (LTR)** profiles; unit/schema/contract tests.
**Deliverables**: `pip install -e` package rendering golden examples on ≥1 OS.
**Validation**: test suite green; 10+ golden samples reviewed by eye, incl. Reference-1 and Reference-3 rebuilds side-by-side.
**Risks**: R-10 (subprocess), R-2 (measurement API design), R-9 (now MVP-critical — fallback decided in Phase 0).
**Exit**: MVP acceptance criteria A1–A5 and A11 met (`12-acceptance-criteria.md`).

## Phase 3 — Browser Gallery & Test Harness

**Goal**: verification infrastructure before feature breadth.
**Scope**: gallery builder + index/detail pages (swimlane samples included); Playwright E2E; screenshot baselines + diff tooling; 3-OS CI matrix; RenderReport metrics (crossings/overlaps/timing); **phase-grouping columns (FR-6.3)**; sequence-diagram layouter + profile (first non-graph family).
**Deliverables**: CI-published gallery artifact; baseline policy documented.
**Validation**: E2E green on 3 OS; deliberate visual change caught by regression in a test PR.
**Risks**: R-21 (baseline churn), R-4 (CI fonts — bundled fonts land here).
**Exit**: MVP acceptance A6–A10 met → **MVP declared** (all A-criteria green).

## Phase 4 — Styling, Themes & Arabic/RTL

**Goal**: full visual control + verified Arabic everywhere first-class.
**Scope**: complete 6-level cascade + presets + RTL-aware built-in themes; font bundling/subsetting/embedding (Cairo default per D10); Arabic measurement validated (uharfbuzz primary, raqm cross-check); RL mirroring through ELK + renderer — lane headers move to right, badge corners mirror, arrows/flow reverse (Reference-2 rebuild is the gate); Arabic golden suite (incl. mixed-script, diacritics); textAsPaths option; per-OS baseline strategy if needed.
**Deliverables**: Arabic/RTL gallery section; `rtl-arabic.md` user guide.
**Validation**: §4 of `07-rtl-arabic-strategy.md` test plan green on 3 OS.
**Risks**: R-1…R-5.
**Exit**: Arabic flowchart + architecture diagrams pixel-stable on 3 OS; native-speaker review of samples (recommend: you).

## Phase 5 — Advanced Layout, Routing Depth & Remaining Families

**Goal**: routing control depth + family breadth (swimlanes already shipped in MVP per D3:B).
**Scope**: hints: waypoints, priority, preferred direction, `respectManualPositions`; crossing/overlap QA metrics gated with agreed thresholds; libavoid evaluation if MVP swimlane/back-edge routing quality insufficient (R-8); swimlane polish: vertical-lane variant hardening, nested lanes (best-effort, AM-6); state + deployment/infrastructure profiles (cheap on existing engine); ER profile with ports.
**Deliverables**: routing-hint demos; threshold-gated benchmark set; new family samples.
**Validation**: crossing metrics ≤ thresholds on benchmark corpus; hint round-trip tests.
**Risks**: R-8/R-13 — libavoid build/bindings cost if triggered.
**Exit**: F5 routing criteria demonstrable; families F1-minus-(class/activity/mindmap) in gallery.

## Phase 6 — Export & Editability

**Goal**: publish/refine/regenerate output roles complete.
**Scope**: PDF (Chromium CDP, per D7); **draw.io and PPTX writers built in parallel (D2:C)** — drawio: pools/lanes/containers/orthogonal points/RTL keys + CLI round-trip tests; PPTX: shapes/connectors/groups/RTL paragraphs + real-PowerPoint checklist; export metadata everywhere; class + mindmap profiles. **Mermaid + PlantUML source writers deferred to a future feature (2026-06-15) — see `docs/spikes/phase-6-progress.md` "Deferred / future tasks".**
**Deliverables**: all export tiers live; `exports/` docs; PowerPoint workflow guide.
**Validation**: drawio opens+re-exports headless in CI; PPTX assertions + manual edit test; lossiness reports reviewed.
**Risks**: R-14…R-19.
**Exit**: Full criteria F5–F7 met.

## Phase 7 — Extensibility & Agent Readiness

**Goal**: third parties (and agents) extend without touching core.
**Scope**: plugin API public + entry-point registry; clone-a-type tutorial (build "incident-flow" type from flowchart in <1 day as the benchmark); agent surface: single `generate(spec) -> artifacts+report` call, JSON error contract, schema bundle published for LLM tool-use; slash-command/skill reference implementation; activity + remaining family polish; v1.0 schema freeze + migration tooling.
**Deliverables**: `extending/` docs; example external plugin repo; agent integration example.
**Validation**: external-style plugin built only from docs (no core edits) passes gallery/tests.
**Risks**: R-26/R-29 (premature freeze) — freeze only after two real plugin exercises.
**Exit**: Full acceptance complete; v1.0 tagged.

---

### Cross-phase rules
- Phase gates are demos + checklists, not dates. No phase starts with red CI.
- Any backend/scope change mid-phase ⇒ ADR + risk-register update.
- The golden corpus only grows; nothing ships without a gallery sample.
