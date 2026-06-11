"""Tarseem CLI (A4): validate / render / export / doctor / examples.

CLI equivalents of the Python API. Reads JSON specs, runs the engine, writes artifacts.
``doctor`` lands in A11; ``examples`` lists the bundled corpus.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tarseem import Engine, __version__
from tarseem.errors import SpecValidationError
from tarseem.validation import validate

SUBCOMMANDS = ("validate", "render", "export", "doctor", "examples")


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
    p_exp.add_argument("-f", "--formats", default="svg", help="comma list: svg,png")
    p_exp.add_argument("-o", "--out", default=".", help="output directory")
    p_exp.add_argument("-n", "--name", default="diagram", help="output basename")
    p_exp.add_argument("--node", default="node", help="Node.js executable (graph families)")
    p_exp.set_defaults(func=_cmd_export)

    p_doc = sub.add_parser("doctor", help="verify Node/elkjs/Playwright/fonts")
    p_doc.add_argument("--json", action="store_true", help="emit a machine-readable report")
    p_doc.set_defaults(func=_cmd_doctor)

    p_ex = sub.add_parser("examples", help="list bundled example specs")
    p_ex.set_defaults(func=_cmd_examples)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 0
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
