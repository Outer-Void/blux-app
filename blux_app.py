#!/usr/bin/env python3
"""BLUX App CLI entrypoint."""

from __future__ import annotations

import argparse
from pathlib import Path

from blux_view import render_from_directory


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="BLUX App read-only viewer.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    view_parser = subparsers.add_parser("view", help="Render a run directory.")
    view_parser.add_argument(
        "--root",
        type=Path,
        required=True,
        help="Root directory containing BLUX JSON artifacts.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "view":
        directory = args.root.expanduser().resolve()
        if not directory.exists():
            raise SystemExit(f"Run directory does not exist: {directory}")
        render_from_directory(directory)


if __name__ == "__main__":
    main()
