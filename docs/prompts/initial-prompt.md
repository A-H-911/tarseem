# Initial Prompt for Claude Code

Copy-paste the block below as your first message in Claude Code (started from the repo root).

---

This repo contains the **approved design** for Tarseem, a schema-driven Python diagram engine. You are starting implementation. `CLAUDE.md` holds the architecture invariants; `docs/plan/` is the approved contract (decisions D1–D12 are final — see `docs/plan/13-open-decisions.md`).

**Step 1 — Orientation (do this first, no code):**
Read `docs/plan/README.md`, `04-architecture.md`, `06-layout-routing-strategy.md`, `07-rtl-arabic-strategy.md`, `11-phased-plan.md`, `12-acceptance-criteria.md`, and `docs/plan/references/analysis.md`. Then give me: (a) a ≤1-page summary of what you'll build and the invariants you must respect, (b) your Phase 0 spike execution plan with proposed file layout under `spikes/`, tools to install, and the PASS/FAIL criteria per spike taken from the plan. **Stop and wait for my approval.**

**Step 2 — Phase 0 spikes (after my approval, one spike at a time):**
Execute the 4 spikes from `docs/plan/11-phased-plan.md` Phase 0, in order:
1. elkjs round-trip: Python ↔ pinned elkjs in a long-lived Node subprocess; 50-node compound graph with ports; measure cold/warm latency.
2. Arabic pipeline: uharfbuzz measurement → SVG with `direction="rtl"` + embedded Cairo font → Playwright/Chromium PNG; verify shaping and node sizing.
3. Swimlane (MVP-gating): rebuild the three reference diagrams (`docs/plan/references/analysis.md`) via ELK partitioning; if it fails the acceptance in `06-layout-routing-strategy.md` §4, demonstrate the pre-approved lane-grid fallback instead.
4. Editable probes: hand-built `.drawio` (pool + 2 lanes + RTL label) that opens correctly in diagrams.net; minimal python-pptx deck (shapes + connector + `rtl="1"` paragraph) that opens correctly in PowerPoint.

Rules: spike code is throwaway, lives in `spikes/spike-N-*/`; each spike ends with `docs/spikes/spike-N-report.md` (what was built, how to run it, screenshots, measurements, PASS/FAIL vs criteria, surprises). Pin every version you install. Pause for my review after each report.

**Step 3 — Phase 0 exit:**
Write `docs/spikes/phase-0-summary.md`: per-spike verdicts, the swimlane path decision (partitioning vs lane-grid), any plan deviations needed, and a go/no-go recommendation for Phase 1. **Stop — do not scaffold the engine package until I approve Phase 1.**

Environment notes: Python ≥3.10 with a project venv; Node LTS for elkjs; `playwright install chromium` after installing Playwright; on Windows remember `pip` + venv quirks and never rely on system fonts for Arabic tests — bundle Cairo font files under `spikes/assets/fonts/`.

---

## Suggested follow-up prompts (later)

- "Phase 0 approved. Begin Phase 1 per docs/plan/11-phased-plan.md: seed ADR-001…005 from docs/plan/04-architecture.md into docs/adr/, propose the package scaffolding and CI skeleton, stop before writing engine code."
- "Begin Phase 2. Work acceptance-criteria-first: pick A1, write the failing tests, implement, repeat. Keep docs/plan/12-acceptance-criteria.md as the checklist and report progress against it."
