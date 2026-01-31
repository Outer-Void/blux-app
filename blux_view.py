#!/usr/bin/env python3
"""Minimal read-only viewer for BLUX artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable, Iterable

PANEL_FILES = [
    ("Intent", "intent.json"),
    ("Reasoning (CogA)", "coga.json"),
    ("Build (cA)", "ca.json"),
    ("Verdicts", "verdicts.json"),
    ("Execution Receipt", "receipt.json"),
    ("Harness Report", "report.json"),
]


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def render_section(title: str, data: Any) -> None:
    print(f"\n== {title} ==")
    print(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True))


def render_missing(title: str, path: Path) -> None:
    print(f"\n== {title} ==")
    print(f"(missing) {path}")


def render_list(title: str, items: Iterable[str]) -> None:
    print(f"\n== {title} ==")
    for item in items:
        print(f"- {item}")


def extract_file_artifacts(data: Any) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    def add_entry(entry: dict[str, Any]) -> None:
        path = entry.get("path") or entry.get("file") or entry.get("filename")
        content = (
            entry.get("content")
            if "content" in entry
            else entry.get("text") or entry.get("body")
        )
        if path is None or content is None:
            return
        key = (str(path), str(content))
        if key in seen:
            return
        seen.add(key)
        artifacts.append({"path": str(path), "content": content})

    def scan(value: Any) -> None:
        if isinstance(value, dict):
            files = value.get("files")
            if isinstance(files, list):
                for item in files:
                    if isinstance(item, dict):
                        add_entry(item)
            artifacts_list = value.get("artifacts")
            if isinstance(artifacts_list, list):
                for item in artifacts_list:
                    scan(item)
            for nested in value.values():
                scan(nested)
        elif isinstance(value, list):
            for item in value:
                scan(item)

    scan(data)
    return artifacts


def render_file_artifacts(data: Any) -> None:
    artifacts = extract_file_artifacts(data)
    if not artifacts:
        return
    render_list(
        "Multi-file Artifacts (File List)",
        [artifact["path"] for artifact in artifacts],
    )
    for artifact in artifacts:
        path = artifact["path"]
        content = artifact["content"]
        title = f"Multi-file Artifact: {path}"
        if isinstance(content, str):
            print(f"\n== {title} ==")
            print(content)
        else:
            render_section(title, content)


def looks_like_unified_diff(value: str) -> bool:
    trimmed = value.lstrip()
    if trimmed.startswith("diff --git"):
        return True
    return "--- " in value and "+++ " in value and "@@" in value


def extract_patch_bundles(data: Any) -> list[str]:
    patches: list[str] = []
    seen: set[str] = set()

    def add_patch(value: str) -> None:
        if value in seen:
            return
        seen.add(value)
        patches.append(value)

    def scan(value: Any, label: str | None = None) -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                key_lower = str(key).lower()
                if key_lower in {"diff", "patch", "patches", "patch_bundle", "bundle"}:
                    scan(nested, key_lower)
                else:
                    scan(nested, label)
        elif isinstance(value, list):
            for item in value:
                scan(item, label)
        elif isinstance(value, str):
            if label and ("patch" in label or "diff" in label or "bundle" in label):
                if looks_like_unified_diff(value):
                    add_patch(value)

    scan(data)
    return patches


def render_patch_bundles(data: Any) -> None:
    patches = extract_patch_bundles(data)
    if not patches:
        return
    for index, patch in enumerate(patches, start=1):
        title = f"Patch Bundle {index} (Unified Diff)"
        print(f"\n== {title} ==")
        print(patch)


def render_coga_extras(data: Any) -> None:
    if not isinstance(data, dict):
        return
    options = data.get("options")
    if isinstance(options, list) and options:
        option_lines = []
        for index, option in enumerate(options, start=1):
            if isinstance(option, dict):
                label = option.get("name") or option.get("title") or option.get("summary")
                option_lines.append(f"{index}. {label or 'Option'}")
            else:
                option_lines.append(f"{index}. {option}")
        render_list("CogA Options", option_lines)
    comparison_matrix = data.get("comparison_matrix")
    if comparison_matrix is not None:
        render_section("CogA Comparison Matrix", comparison_matrix)


def render_receipt_extras(data: Any) -> None:
    if not isinstance(data, dict):
        return
    agent_runs = data.get("agent_runs")
    if isinstance(agent_runs, list) and agent_runs:
        lines = []
        for run in agent_runs:
            if isinstance(run, dict):
                identifier = run.get("id") or run.get("name") or "run"
                status = run.get("status") or "unknown"
                started = run.get("started_at") or run.get("start_time")
                ended = run.get("ended_at") or run.get("end_time")
                timeline = " -> ".join([value for value in [started, ended] if value])
                if timeline:
                    lines.append(f"{identifier}: {status} ({timeline})")
                else:
                    lines.append(f"{identifier}: {status}")
            else:
                lines.append(str(run))
        render_list("Receipt Agent Runs", lines)
    versions = data.get("versions")
    if isinstance(versions, dict) and versions:
        render_section("Receipt Versions", versions)
    hashes = data.get("hashes")
    if isinstance(hashes, dict) and hashes:
        render_section("Receipt Hashes", hashes)


def summarize_fixtures(fixtures: list[Any]) -> dict[str, int]:
    summary = {"passed": 0, "failed": 0, "skipped": 0, "total": 0}
    for fixture in fixtures:
        status = None
        if isinstance(fixture, dict):
            status = fixture.get("status")
            if status is None:
                passed = fixture.get("passed")
                if passed is True:
                    status = "passed"
                elif passed is False:
                    status = "failed"
        if status:
            normalized = str(status).lower()
            if normalized.startswith("pass"):
                summary["passed"] += 1
            elif normalized.startswith("skip"):
                summary["skipped"] += 1
            else:
                summary["failed"] += 1
        summary["total"] += 1
    return summary


def render_harness_report(data: Any) -> None:
    if not isinstance(data, dict):
        return
    summary = data.get("summary") or data.get("totals") or data.get("results_summary")
    if summary is not None:
        render_section("Harness Report Summary", summary)
    fixtures = data.get("fixtures") or data.get("results") or data.get("cases")
    if isinstance(fixtures, list) and fixtures:
        if summary is None:
            render_section("Harness Report Summary", summarize_fixtures(fixtures))
        lines = []
        for fixture in fixtures:
            if isinstance(fixture, dict):
                name = fixture.get("name") or fixture.get("id") or "fixture"
                status = fixture.get("status") or ("passed" if fixture.get("passed") else "failed")
                duration = fixture.get("duration_ms") or fixture.get("duration")
                if duration is not None:
                    lines.append(f"{name}: {status} ({duration})")
                else:
                    lines.append(f"{name}: {status}")
            else:
                lines.append(str(fixture))
        render_list("Harness Fixtures", lines)


def render_build_extras(data: Any) -> None:
    render_file_artifacts(data)
    render_patch_bundles(data)


def render_panel(
    title: str,
    path: Path,
    extra_renderer: Callable[[Any], None] | None = None,
) -> None:
    if path.is_file():
        data = load_json(path)
        render_section(title, data)
        if extra_renderer:
            extra_renderer(data)
    else:
        render_missing(title, path)


def render_from_directory(directory: Path) -> None:
    renderers = {
        "Reasoning (CogA)": render_coga_extras,
        "Build (cA)": render_build_extras,
        "Execution Receipt": render_receipt_extras,
        "Harness Report": render_harness_report,
    }
    for title, filename in PANEL_FILES:
        path = directory / filename
        render_panel(title, path, renderers.get(title))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="BLUX App read-only viewer (JSON only).",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help=(
            "Directory containing intent.json, coga.json, ca.json, verdicts.json, "
            "receipt.json, report.json"
        ),
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
