# Tarseem

Schema-driven Python diagram engine: validated JSON specs to architecture-grade diagrams,
with first-class Arabic/RTL and editable exports (draw.io, PPTX).

Status: **Phase 1 scaffold** - no engine logic yet; packages are placeholders implemented in
later phases per `docs/plan/11-phased-plan.md`.

- Design contract (read-only): `docs/plan/`
- Architecture decisions: `docs/adr/` (ADR-001..005)
- Phase 0 validation: `docs/spikes/phase-0-summary.md`

## Development

- Python >= 3.10. Layout runs in a Node subprocess (vendored elkjs); rendering via Playwright/Chromium.
- Setup: `python -m venv .venv` then `pip install -e ".[dev]"` (Phase 2+: `playwright install chromium`).
- Test: `pytest` - Lint: `ruff check .` - Types: `mypy`.

## License

Apache-2.0 (see `LICENSE`).
