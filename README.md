# Tarseem (ترسيم)

**Schema-driven Python diagram engine** — validated JSON specs → architecture-grade diagrams: SVG/PNG/PDF, editable draw.io & PowerPoint (PPTX), with ELK auto-layout, enterprise swimlanes, and Arabic/RTL-first rendering.

> ترسيم: "diagramming / charting". One JSON spec in — publishable, editable, and regenerable diagrams out.

## Status

🚧 **Pre-implementation.** The full research & design mission is complete and approved; implementation follows the phased plan starting with Phase 0 spikes.

- 📐 Approved design & plan: [`docs/plan/`](docs/plan/README.md) (start at the index)
- 🤖 Built with Claude Code — kickoff prompt: [`docs/prompts/initial-prompt.md`](docs/prompts/initial-prompt.md), working memory: [`CLAUDE.md`](CLAUDE.md)
- 🗺️ Roadmap: [`docs/plan/11-phased-plan.md`](docs/plan/11-phased-plan.md) · Acceptance: [`docs/plan/12-acceptance-criteria.md`](docs/plan/12-acceptance-criteria.md)

## Why

No existing tool combines: JSON-native specs (agent-friendly), horizontal/vertical swimlanes, correct Arabic shaping + RTL layout mirroring, controlled orthogonal routing with ports, and *editable* exports (draw.io, native PPTX shapes) — verified across 16 candidate engines in [`docs/plan/03-engine-comparison.md`](docs/plan/03-engine-comparison.md). Tarseem composes the best of them behind one Python API:

**ELK** (layout) · **own SVG renderer** (control) · **Playwright/Chromium** (raster/PDF + Arabic correctness + E2E) · **own draw.io & PPTX writers** (editability).

## Planned MVP

4 diagram families (flowchart, architecture/C4, dependency, swimlane) → SVG/PNG + browser gallery + visual-regression tests, clean Python API + CLI. Then: Arabic/RTL validation, routing depth, PDF + editable/source exports, plugin & agent surface.

## License

Apache-2.0
