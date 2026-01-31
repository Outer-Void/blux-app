#!/usr/bin/env python3
"""Minimal read-only viewer for BLUX artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

PANEL_FILES = {
    "Intent": "intent.json",
    "Reasoning (CogA)": "coga.json",
    "Build (cA)": "ca.json",
    "Verdicts": "verdicts.json",
    "Execution Receipt": "receipt.json",
}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def render_section(title: str, data: Any) -> None:
    print(f"\n== {title} ==")
    print(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True))


def render_missing(title: str, path: Path) -> None:
    print(f"\n== {title} ==")
    print(f"(missing) {path}")


def render_from_directory(directory: Path) -> None:
    for title, filename in PANEL_FILES.items():
        path = directory / filename
        if path.is_file():
            render_section(title, load_json(path))
        else:
            render_missing(title, path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="BLUX App read-only viewer (JSON only).",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Directory containing intent.json, coga.json, ca.json, verdicts.json, receipt.json",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    directory = args.input_dir.expanduser().resolve()
    if not directory.exists():
        raise SystemExit(f"Input directory does not exist: {directory}")
    render_from_directory(directory)


if __name__ == "__main__":
    main()
