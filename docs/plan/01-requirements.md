# Requirements Document — Schema-Driven Python Diagram Engine

Status: Draft for approval · Version 0.1 · 2026-06-11
Scope source: Project mission brief (preserved intent, no scope reduction).

---

## 1. Vision

A reusable, extensible, schema-driven Python diagram engine that orchestrates mature external layout/rendering engines behind a unified API. It generates architecture-grade diagrams from validated JSON specifications, with strong visual control, Arabic/RTL support, swimlanes, controlled edge routing, multiple export formats (static + editable), browser-based verification, and future readiness for AI agents and slash commands.

The engine is a **wrapper/orchestration layer**, not a from-scratch renderer — except where research shows ownership is cheaper than delegation (see ADR in `04-architecture.md`).

## 2. Functional Requirements

### FR-1 Python Wrapper Engine
| ID | Requirement | Priority |
|---|---|---|
| FR-1.1 | Unified Python API: `load → validate → layout → render → export` over all backends | MVP |
| FR-1.2 | Stable normalized internal diagram model (IR) decoupled from any backend | MVP |
| FR-1.3 | Adapter-based backend integration; engine-specific complexity hidden behind interfaces | MVP |
| FR-1.4 | Clean separation: spec / validation / model / layout / render / export layers | MVP |
| FR-1.5 | CLI entry point (`diagram render spec.json --format svg`) | MVP |
| FR-1.6 | Capability negotiation: adapters declare supported features; engine reports degradations explicitly | MVP |

### FR-2 Unified JSON Schema Specification
| ID | Requirement | Priority |
|---|---|---|
| FR-2.1 | All diagrams defined by a single versioned JSON schema (core + typed extensions) | MVP |
| FR-2.2 | Schema covers: nodes, edges, groups/containers, lanes, nesting, labels, annotations, metadata, styles, themes, layout hints, routing hints, export options, per-type extensions | MVP core; full set phased |
| FR-2.3 | Validation: structural (JSON Schema 2020-12) + semantic (referential integrity, cycles, capability checks) | MVP |
| FR-2.4 | Schema versioned (`specVersion`), backward-compatibility policy + migration tooling | MVP policy; migration tooling Full |
| FR-2.5 | Authorable by humans and AI agents; machine-readable error messages with JSON paths | MVP |
| FR-2.6 | No ad-hoc per-diagram-type formats; diagram types are schema extensions of the core | MVP |

### FR-3 Diagram Coverage
| Family | Target phase | Notes |
|---|---|---|
| Flowchart | MVP | Core graph + ELK layered layout |
| Architecture / component / system context / integration / service interaction | MVP | One "boxes-containers-edges" family with profiles |
| C4 (context, container, component) | MVP | Modeled as styled architecture profile |
| Swimlane / cross-functional process | **MVP (per D3:B)** — Phase 0 spike gates approach | ELK partitioning (fallback: lane-grid) + native draw.io lanes on export; visual target = `references/analysis.md` |
| Sequence | Phase 2–3 | Deterministic custom layout (no ELK needed) |
| Deployment / infrastructure | Phase 5 | Architecture profile + icon sets |
| State | Phase 5 | Graph family variant |
| Activity | Phase 5+ | Flowchart variant; lanes optional |
| ER | Phase 5+ | Table-shaped nodes + port-based edges |
| Class | Phase 6+ | Compartment nodes; UML arrowheads |
| Dependency graph | MVP-adjacent | Same engine as flowchart |
| Mind map | Phase 6+ | ELK mrtree/radial |

Deferral rationale and risk per family: see `02-risks.md` and `11-phased-plan.md`.

### FR-4 RTL and Arabic Support
| ID | Requirement | Priority |
|---|---|---|
| FR-4.1 | Arabic labels render correctly (shaping + bidi) in nodes, edges, lanes, groups, titles, legends, annotations | Phase 4 (design from day 1) |
| FR-4.2 | Correctness preserved in all first-class exports (SVG, PNG, PDF, HTML, draw.io, PPTX) | Phase 4–6 |
| FR-4.3 | RTL layout mirroring (diagram flows right→left), independent of text direction | Phase 4 |
| FR-4.4 | Explicit font strategy: bundled dual-script fonts, embedding, fallback chain, cross-platform behavior | Phase 4 |
| FR-4.5 | Text measurement accounts for Arabic shaping (node auto-sizing) | MVP architecture; validated Phase 4 |
| FR-4.6 | Mixed Arabic/Latin labels handled (bidi runs) | Phase 4 |

### FR-5 Visual Control and Styling
| ID | Requirement | Priority |
|---|---|---|
| FR-5.1 | Controllable: size, shape, colors, borders + styles, fonts (family/size/weight), direction, position, spacing, alignment | MVP basic; full Phase 4 |
| FR-5.2 | Six-level style cascade: global theme → diagram → group/container → node → edge → label | MVP |
| FR-5.3 | Reusable named style presets (`styleRefs`), local overrides win | MVP |
| FR-5.4 | Themes portable across rendering backends (style model is backend-neutral; adapters translate) | MVP design |
| FR-5.5 | Built-in themes incl. at least one RTL-aware theme | Phase 4 |

### FR-6 Swimlanes
| ID | Requirement | Priority |
|---|---|---|
| FR-6.1 | Horizontal and vertical lanes; lane labels; per-lane styling (hue→header/band/node tints); visual separation; title bar | MVP (P2–3) |
| FR-6.2 | Cross-lane flows with orthogonal routing, incl. back-edges and long multi-lane edges | MVP (P2–3) |
| FR-6.3 | Phase grouping (columns crossing lanes) | MVP (P3) |
| FR-6.4 | Nested lanes where practical (flagged: limited engine support) | Full, best-effort |
| FR-6.5 | Reproduce enterprise/presentation-style swimlanes per `references/analysis.md` (LTR in MVP; RTL variant in Phase 4) | MVP gate (A12) |
| FR-6.6 | Editable swimlane export to draw.io native pool/lane shapes | Phase 6 |

### FR-7 Edge Routing
| ID | Requirement | Priority |
|---|---|---|
| FR-7.1 | Orthogonal, polyline, and curved routing modes | MVP (via ELK) |
| FR-7.2 | Automatic crossing minimization | MVP (ELK layered) |
| FR-7.3 | Routing around nodes/containers/lanes/labels | MVP (engine-level), refined Phase 5 |
| FR-7.4 | Ports/anchors on nodes (sides, fixed positions, order) | MVP schema + ELK |
| FR-7.5 | Hints: preferred direction, waypoints, edge priority, avoid zones | Phased: direction+waypoints Phase 5; avoid zones Full/best-effort |
| FR-7.6 | Manual waypoints respected on re-render | Phase 5 |

### FR-8 Cross-Platform
| ID | Requirement | Priority |
|---|---|---|
| FR-8.1 | Windows, macOS, Linux support for core pipeline | MVP one OS green; all three by Phase 3 CI |
| FR-8.2 | OS-specific tools isolated behind optional adapters (e.g., Inkscape EMF = Windows-only optional) | Always |
| FR-8.3 | CI execution on all three OSes (GitHub Actions matrix) | Phase 3 |
| FR-8.4 | Declared, pinned external dependencies (Node runtime, Playwright browsers, fonts) with install doctor command | Phase 2–3 |

### FR-9 Testability and Extensibility
| ID | Requirement | Priority |
|---|---|---|
| FR-9.1 | Test levels: schema, unit, adapter contract, rendering, integration, export, browser E2E, visual regression, sample gallery | Phased per `09-testing-gallery-strategy.md` |
| FR-9.2 | New diagram types added via plugin (schema extension + compile/layout/render profiles), no core rewrite | Phase 7 model; architecture from MVP |
| FR-9.3 | Diagram types clonable/customizable from built-ins | Phase 7 |
| FR-9.4 | No hardcoded monolith; registries for adapters, themes, shapes, diagram types | MVP |

### FR-10 Documentation
Per `10-documentation-plan.md`: architecture, ADRs, schema reference (generated), examples gallery, extension guide, RTL guide, export guide, troubleshooting, roadmap. Audiences: developers, architects, AI agents, maintainers, spec authors.

### FR-11 Export and Editability
| ID | Requirement | Tier | Priority |
|---|---|---|---|
| FR-11.1 | SVG (canonical, self-contained option with embedded fonts) | First-class | MVP |
| FR-11.2 | PNG (scale factor control) | First-class | MVP |
| FR-11.3 | HTML preview/gallery | First-class | MVP/Phase 3 |
| FR-11.4 | PDF | First-class | Phase 6 |
| FR-11.5 | draw.io XML with native shapes/lanes + embedded geometry (editable) | First-class editable | Phase 6 |
| FR-11.6 | PPTX native shapes via python-pptx (editable in PowerPoint) | Adapter | Phase 6 |
| FR-11.7 | Mermaid source export (regeneration) | Best-effort | Future (deferred 2026-06-15) |
| FR-11.8 | PlantUML source export (regeneration) | Best-effort | Future (deferred 2026-06-15) |
| FR-11.9 | JSON spec is always the authoritative "source output" | First-class | MVP |
| FR-11.10 | Four output roles distinguished: publish (static) / refine (editable) / regenerate (source) / verify (browser) | MVP concept |

## 3. Non-Functional Requirements

| ID | Requirement |
|---|---|
| NFR-1 | Deterministic output: same spec + version ⇒ identical layout/render (fixed seeds, pinned engines) |
| NFR-2 | Performance: ≤ 2 s render for ≤ 100-node diagram (warm process); layout subprocess kept alive |
| NFR-3 | Licensing: core distributable under permissive license; no GPL in required path (OGDF excluded); no mandatory commercial deps (GoJS, TALA, JointJS+ optional at most); bpmn.io watermark constraint surfaced if BPMN adapter added |
| NFR-4 | Observability: structured render logs, failed-render detection, machine-readable error reports |
| NFR-5 | Agent-readiness: pure-function API (spec in → artifacts out), JSON errors, no interactive prompts |
| NFR-6 | Versioned artifacts: outputs embed spec hash + engine versions in metadata |
| NFR-7 | Offline-capable: no required network calls at render time (Kroki optional only) |

## 4. Constraints

1. Python ≥ 3.10 orchestration layer.
2. External engines only via documented adapter boundaries.
3. Node.js runtime required for the primary layout backend (elkjs) — isolated behind the layout service interface; acceptance pending (Open Decision D1).
4. Playwright-managed Chromium required for canonical raster/PDF export and Arabic correctness.
5. CairoSVG must not be used anywhere Arabic text is possible (verified unsupported).
6. No implementation before approval of this mission's outputs.

## 5. Assumptions (explicit, require confirmation)

| ID | Assumption | Risk if wrong |
|---|---|---|
| A-1 | ~~Node.js dependency acceptable~~ **Resolved: accepted (D1)** | — |
| A-2 | Editable output priority is PowerPoint-centric (draw.io + PPTX), not Visio | Add VSDX adapter work |
| A-3 | Diagrams are batch-generated (no live interactive editor in scope) | Different architecture (JS-first) |
| A-4 | Arabic is the only required RTL script initially (Hebrew etc. later) | Minor — same pipeline |
| A-5 | Typical diagram size ≤ ~300 nodes | Performance work needed |
| A-6 | ~~Reference images pending~~ **Resolved: provided (D9)** — analyzed in `references/analysis.md` | — |

## 6. Open Questions

**All resolved 2026-06-11** — see decision record `13-open-decisions.md` (D1–D12). Material outcomes: D3:B moves swimlanes into MVP; D2:C runs drawio+PPTX writers in parallel (Phase 6).

## 7. Acceptance Criteria

See `12-acceptance-criteria.md` (MVP and Full Target, both testable).
