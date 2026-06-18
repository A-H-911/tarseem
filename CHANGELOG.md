# Changelog

All notable changes follow [Keep a Changelog](https://keepachangelog.com/) and Semantic Versioning.

## [Unreleased]

_Nothing yet._

## [1.0.0] - 2026-06-17

First stable release. Schema **frozen at v1.0** (ADR-009); full acceptance F1–F12 met
(`docs/phase-7-acceptance-audit.md`).

### Added
- **Eleven diagram families**: flowchart, architecture / C4, dependency, swimlane (horizontal +
  vertical, phases, nested), sequence, ER, state, deployment, UML class, mindmap, and activity.
- **One positioned IR, many writers**: SVG (canonical) + PNG / PDF via Chromium + editable
  **draw.io** (ADR-007) and **PPTX** writers, each returning an honest `CapabilityReport`.
- **First-class Arabic / RTL**: HarfBuzz shaping before layout, geometry-only RL mirroring, bundled
  Cairo font; per-OS visual baselines on Windows / macOS / Linux.
- **Agent surface**: pure `generate(spec) → JSON` (never raises on a bad spec; `{code, path,
  message, hint}` error contract), `schema_bundle()`, CLI `generate` / `schema` / `migrate`, and a
  reference skill (`integrations/claude-skill/SKILL.md`).
- **Extensibility**: diagram types are entry-point plugins (ADR-008); the built-ins register through
  the same public mechanism, with two external example plugins under `examples/plugins/`.
- **Schema v1.0 freeze** with versioning + `tarseem migrate` tooling.
- **Determinism**: pinned elkjs + Chromium; content-addressed provenance (spec hash + engine
  versions); same spec ⇒ byte-identical output.
- **Performance**: process-wide Chromium pool + reusable ELK Node session for batch rendering.
- **Docs**: guides (quickstart, families, RTL/Arabic, exports, PowerPoint, agents, extending,
  limitations, troubleshooting) and ADR-001…009.

### Deferred (non-blocking)
- Mermaid / PlantUML source writers; a searchable-Arabic PDF text layer; the mkdocs-material site +
  auto-generated per-object schema reference.
