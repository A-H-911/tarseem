"""Tarseem CLI (A4): validate / render / export / doctor / examples.

CLI equivalents of the Python API. Reads JSON specs, runs the engine, writes artifacts.
``doctor`` lands in A11; ``examples`` lists the bundled corpus.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tarseem import Engine, __version__
from tarseem.errors import SpecValidationError
from tarseem.validation import validate

SUBCOMMANDS = (
    "validate", "render", "export", "generate", "schema", "migrate", "doctor", "examples",
    "gallery",
)


def _load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _cmd_validate(args: argparse.Namespace) -> int:
    result = validate(_load(args.spec))
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0 if result.ok else 1


def _cmd_render(args: argparse.Namespace) -> int:
    try:
        result = Engine(node=args.node).render(_load(args.spec))
    except SpecValidationError as exc:
        print(json.dumps(exc.result.to_dict(), ensure_ascii=False, indent=2))
        return 1
    out = Path(args.out) if args.out else Path("diagram.svg")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(result.to_svg(provenance=True), encoding="utf-8")
    print(f"wrote {out}")
    return 0


def _cmd_export(args: argparse.Namespace) -> int:
    try:
        result = Engine(node=args.node).render(_load(args.spec))
    except SpecValidationError as exc:
        print(json.dumps(exc.result.to_dict(), ensure_ascii=False, indent=2))
        return 1
    formats = [f.strip() for f in args.formats.split(",") if f.strip()]
    written = result.export(formats, args.out, name=args.name)
    for fmt, path in written.items():
        print(f"{fmt}: {path}")
    for fmt, report in result.reports.items():
        if report.lossy:
            print(f"  [{fmt}] capability report: {len(report.warnings)} note(s)")
            for w in report.warnings:
                where = f" ({w.element})" if w.element else ""
                print(f"    - {w.feature}: {w.message}{where}")
    return 0


def _cmd_generate(args: argparse.Namespace) -> int:
    """Agent surface from the CLI: JSON payload (artifacts + report) to stdout, never raises."""
    from tarseem import generate

    payload = generate(
        _load(args.spec), formats=args.formats, out_dir=args.out, name=args.name, node=args.node
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("ok") else 1


def _cmd_schema(args: argparse.Namespace) -> int:
    """Emit the published JSON-Schema bundle (IDE ``$schema`` / LLM tool-use)."""
    from tarseem.schema import schema_bundle

    text = json.dumps(schema_bundle(), ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(text)
    return 0


def _cmd_migrate(args: argparse.Namespace) -> int:
    """Upgrade a spec to the current schema version (v1.0): bump specVersion, drop dropped keys."""
    from tarseem.migrate import migrate_spec

    text = json.dumps(migrate_spec(_load(args.spec)), ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(text)
    return 0


def _cmd_doctor(args: argparse.Namespace) -> int:
    from tarseem.doctor import run_doctor

    report = run_doctor()
    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        for check in report.checks:
            mark = "OK  " if check.ok else "FAIL"
            print(f"[{mark}] {check.name:11} {check.detail}")
            if not check.ok and check.hint:
                print(f"       -> {check.hint}")
        print("doctor: all checks passed." if report.ok else "doctor: problems found (see above).")
    return 0 if report.ok else 1


def _cmd_examples(args: argparse.Namespace) -> int:
    examples = sorted(Path("examples").glob("*.json"))
    for path in examples:
        print(path.name)
    return 0


def _cmd_gallery(args: argparse.Namespace) -> int:
    from tarseem.gallery import build_gallery

    paths = sorted(Path(args.examples).glob("*.json"))
    if not paths:
        print(f"no specs found in {args.examples}")
        return 1
    result = build_gallery(paths, Path(args.out), with_png=not args.no_png, node=args.node)
    failed = [s for s in result.samples if not s.ok]
    for s in result.samples:
        mark = "ok  " if s.ok else "FAIL"
        print(f"[{mark}] {s.name}" + (f"  -> {s.error}" if not s.ok else ""))
    print(f"gallery: {result.index_path}  ({len(result.samples) - len(failed)}/"
          f"{len(result.samples)} rendered)")
    return 1 if failed else 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tarseem", description="Tarseem diagram engine.")
    parser.add_argument("--version", action="version", version=f"tarseem {__version__}")
    sub = parser.add_subparsers(dest="command")

    p_val = sub.add_parser("validate", help="validate a spec; coded errors to stdout")
    p_val.add_argument("spec", help="path to a JSON spec")
    p_val.set_defaults(func=_cmd_validate)

    p_ren = sub.add_parser("render", help="render a spec to SVG")
    p_ren.add_argument("spec")
    p_ren.add_argument("-o", "--out", help="output .svg path (default: diagram.svg)")
    p_ren.add_argument("--node", default="node", help="Node.js executable (graph families)")
    p_ren.set_defaults(func=_cmd_render)

    p_exp = sub.add_parser("export", help="export a spec to one or more formats")
    p_exp.add_argument("spec")
    p_exp.add_argument(
        "-f", "--formats", default="svg", help="comma list: svg,png,pdf,drawio,pptx"
    )
    p_exp.add_argument("-o", "--out", default=".", help="output directory")
    p_exp.add_argument("-n", "--name", default="diagram", help="output basename")
    p_exp.add_argument("--node", default="node", help="Node.js executable (graph families)")
    p_exp.set_defaults(func=_cmd_export)

    p_gen = sub.add_parser("generate", help="agent surface: render -> JSON {artifacts, report}")
    p_gen.add_argument("spec")
    p_gen.add_argument("-f", "--formats", default="svg", help="comma list: svg,png,pdf,drawio,pptx")
    p_gen.add_argument("-o", "--out", help="output directory (required for non-SVG formats)")
    p_gen.add_argument("-n", "--name", default="diagram", help="output basename")
    p_gen.add_argument("--node", default="node", help="Node.js executable (graph families)")
    p_gen.set_defaults(func=_cmd_generate)

    p_sch = sub.add_parser("schema", help="emit the JSON-Schema bundle (IDE / LLM tool-use)")
    p_sch.add_argument("-o", "--out", help="output .json path (default: stdout)")
    p_sch.set_defaults(func=_cmd_schema)

    p_mig = sub.add_parser("migrate", help="upgrade a spec to the current schema version (1.0)")
    p_mig.add_argument("spec")
    p_mig.add_argument("-o", "--out", help="output .json path (default: stdout)")
    p_mig.set_defaults(func=_cmd_migrate)

    p_doc = sub.add_parser("doctor", help="verify Node/elkjs/Playwright/fonts")
    p_doc.add_argument("--json", action="store_true", help="emit a machine-readable report")
    p_doc.set_defaults(func=_cmd_doctor)

    p_ex = sub.add_parser("examples", help="list bundled example specs")
    p_ex.set_defaults(func=_cmd_examples)

    p_gal = sub.add_parser("gallery", help="build the static HTML gallery from examples/")
    p_gal.add_argument("--examples", default="examples", help="directory of JSON specs")
    p_gal.add_argument("-o", "--out", default="gallery", help="output directory")
    p_gal.add_argument("--no-png", action="store_true", help="skip PNG thumbnails (faster)")
    p_gal.add_argument("--node", default="node", help="Node.js executable (graph families)")
    p_gal.set_defaults(func=_cmd_gallery)
    return parser


def _force_utf8_stdio() -> None:
    """Emit UTF-8 regardless of platform. Windows consoles default to cp1252, which cannot
    encode Arabic — e.g. the ``doctor`` shaping probe or RTL spec output would crash. Best
    effort: a stream without ``reconfigure`` (already wrapped/redirected) is left as-is."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8")
            except (ValueError, OSError):
                pass


def main(argv: list[str] | None = None) -> int:
    _force_utf8_stdio()
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 0
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
