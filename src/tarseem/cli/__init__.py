"""Minimal CLI bootstrap. Subcommands are stubs until Phase 2 (no engine logic yet)."""
from __future__ import annotations

import argparse

from tarseem import __version__

SUBCOMMANDS = ("validate", "render", "export", "doctor", "examples")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tarseem", description="Tarseem diagram engine (scaffold)."
    )
    parser.add_argument("--version", action="version", version=f"tarseem {__version__}")
    sub = parser.add_subparsers(dest="command")
    for name in SUBCOMMANDS:
        sub.add_parser(name, help=f"{name} (not implemented in Phase 1)")
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 0
    print(f"tarseem {args.command}: not implemented yet (Phase 1 scaffold).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
