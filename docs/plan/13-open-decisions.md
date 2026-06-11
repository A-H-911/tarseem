# Open Decisions — RESOLVED 2026-06-11

All decisions taken by Anas on 2026-06-11. This file is now the decision record; deviations from original recommendations are marked ⚠ with consequences.

| ID | Decision | Outcome | Notes / consequences |
|---|---|---|---|
| **D1** | Node.js as managed runtime dep (elkjs primary) | ✅ **Yes** | ELK confirmed primary; vendored pinned bundle + `doctor` checks |
| **D2** | Editable-output order | ⚠ **C — drawio + PPTX in parallel** (rec. was sequential) | Phase 6 runs both writer tracks concurrently; slightly higher peak effort, earlier PPTX feedback |
| **D3** | MVP diagram families | ⚠ **B — swimlane added to MVP** (rec. deferred to P5) | MVP = flowchart, architecture/C4, dependency, **swimlane** (+sequence in P3). Phase plan restructured; Phase 0 swimlane spike becomes MVP-gating; lane-grid fallback pre-approved (R-9 now MVP-critical) |
| **D4** | Schema stance: core + profiles + namespaced extensions | ✅ Confirmed | |
| **D5** | bpmn-js adapter | ✅ **A — excluded** (watermark) | |
| **D6** | D2/TALA commercial adapter | ✅ **A — no** | |
| **D7** | PDF backend | ✅ **A — Chromium print-to-PDF only** | |
| **D8** | Distribution | ✅ **Apache-2.0; single package, entry-point plugins until P7** | |
| **D9** | Swimlane reference images | ✅ **Provided** (3 images: LTR, RTL-Arabic, shape-variety) | Analysis: `references/analysis.md`; binds MVP A12 + F3 acceptance |
| **D10** | Default dual-script font | ✅ **A — Cairo** (+ Noto pair fallback) | |
| **D11** | Performance targets (NFR-2) | ✅ Confirmed | ≤100 nodes ≤2 s warm; ≤300 supported |
| **D12** | Kroki optional client extra | ✅ **A — yes, off by default** | |

**Status: mission approved with the above decisions. Next gate: Phase 0 spike results.**
