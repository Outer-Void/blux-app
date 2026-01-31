#!/usr/bin/env python3
"""Minimal read-only viewer for BLUX artifacts."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

PANEL_FILES = [
    ("Intent", "intent.json"),
    ("Reasoning (CogA)", "coga.json"),
    ("Build (cA)", "ca.json"),
    ("Verdicts", "verdicts.json"),
    ("Execution Receipt", "receipt.json"),
    ("Execution Receipt (System)", "execution_receipt.json"),
    ("Replay Report", "replay_report.json"),
    ("Acceptance Report", "accept_report.json"),
    ("Harness Report", "report.json"),
]

KNOWN_JSON_FILES = {filename for _, filename in PANEL_FILES}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


@dataclass(frozen=True)
class ViewerContext:
    directory: Path
    data_by_filename: dict[str, Any]

    def get(self, filename: str) -> Any | None:
        return self.data_by_filename.get(filename)


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

    render_run_graph(data)
    render_version_negotiation(data)


def render_replay_report_extras(data: Any) -> None:
    if not isinstance(data, dict):
        return
    fixtures = data.get("fixtures") or data.get("results") or data.get("cases")
    if isinstance(fixtures, list) and fixtures:
        render_list(
            "Replay Fixtures",
            [format_fixture_line(fixture) for fixture in fixtures],
        )


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


def render_acceptance_report(data: Any) -> None:
    if not isinstance(data, dict):
        return
    verdicts = data.get("verdicts") or data.get("acceptance") or data.get("results")
    if isinstance(verdicts, list) and verdicts:
        render_list(
            "Acceptance Verdicts",
            [format_fixture_line(verdict) for verdict in verdicts],
        )


def format_fixture_line(fixture: Any) -> str:
    if isinstance(fixture, dict):
        name = fixture.get("name") or fixture.get("id") or fixture.get("fixture") or "fixture"
        status = fixture.get("status") or fixture.get("verdict") or "unknown"
        details = fixture.get("details") or fixture.get("note")
        if details:
            return f"{name}: {status} ({details})"
        return f"{name}: {status}"
    return str(fixture)


def render_run_graph(data: Any) -> None:
    steps = extract_run_steps(data)
    if not steps:
        return
    lines = []
    for index, step in enumerate(steps, start=1):
        identifier = step.get("id") or step.get("name") or f"step-{index}"
        status = step.get("status") or step.get("state") or "unknown"
        hash_value = (
            step.get("hash")
            or step.get("content_hash")
            or step.get("digest")
            or step.get("sha")
        )
        timing = step.get("started_at") or step.get("start_time")
        ended = step.get("ended_at") or step.get("end_time")
        if timing or ended:
            timeline = " -> ".join([value for value in [timing, ended] if value])
        else:
            timeline = None
        suffix = []
        if hash_value:
            suffix.append(f"hash={hash_value}")
        if timeline:
            suffix.append(timeline)
        if suffix:
            lines.append(f"{identifier}: {status} ({', '.join(suffix)})")
        else:
            lines.append(f"{identifier}: {status}")
    render_list("Run Steps", lines)


def extract_run_steps(data: Any) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    seen: set[int] = set()

    def add_step(value: Any) -> None:
        if not isinstance(value, dict):
            return
        identifier = id(value)
        if identifier in seen:
            return
        seen.add(identifier)
        steps.append(value)

    def scan(value: Any) -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                key_lower = str(key).lower()
                if key_lower in {"steps", "run_steps", "timeline", "nodes"} and isinstance(
                    nested, list
                ):
                    for item in nested:
                        if isinstance(item, dict):
                            add_step(item)
                elif key_lower in {"run_graph", "graph"}:
                    scan(nested)
                else:
                    scan(nested)
        elif isinstance(value, list):
            for item in value:
                scan(item)

    scan(data)
    return steps


def render_version_negotiation(data: Any) -> None:
    versions = extract_version_negotiation(data)
    if versions:
        render_list("Version Negotiation", versions)


def extract_version_negotiation(data: Any) -> list[str]:
    lines: list[str] = []
    if not isinstance(data, dict):
        return lines

    agent_runs = data.get("agent_runs")
    if isinstance(agent_runs, list):
        for run in agent_runs:
            if not isinstance(run, dict):
                continue
            identifier = run.get("id") or run.get("name") or "run"
            requested = (
                run.get("requested_version")
                or run.get("requested")
                or run.get("requested_range")
            )
            resolved = run.get("resolved_version") or run.get("resolved")
            if requested or resolved:
                lines.append(f"{identifier}: requested={requested}, resolved={resolved}")

    requested_versions = data.get("requested_versions")
    resolved_versions = data.get("resolved_versions")
    if isinstance(requested_versions, dict) or isinstance(resolved_versions, dict):
        requested_versions = requested_versions if isinstance(requested_versions, dict) else {}
        resolved_versions = resolved_versions if isinstance(resolved_versions, dict) else {}
        for key in sorted(set(requested_versions) | set(resolved_versions)):
            requested = requested_versions.get(key)
            resolved = resolved_versions.get(key)
            lines.append(f"{key}: requested={requested}, resolved={resolved}")

    negotiation = data.get("version_negotiation")
    if isinstance(negotiation, dict):
        for key, value in negotiation.items():
            if isinstance(value, dict):
                requested = value.get("requested") or value.get("requested_version")
                resolved = value.get("resolved") or value.get("resolved_version")
                lines.append(f"{key}: requested={requested}, resolved={resolved}")
    return lines


def render_dataset_linkage(receipt: Any, replay_report: Any) -> None:
    fixtures = extract_fixture_refs(receipt)
    if not fixtures:
        return
    verification = build_fixture_verification(replay_report)
    lines = []
    for fixture in fixtures:
        fixture_id = fixture.get("id") or fixture.get("fixture_id") or fixture.get("name")
        fixture_hash = fixture.get("hash") or fixture.get("content_hash")
        lookup_key = fixture_id or fixture_hash
        status = verification.get(lookup_key, "unknown")
        badge = status_to_badge(status)
        details = []
        if fixture_id:
            details.append(f"id={fixture_id}")
        if fixture_hash:
            details.append(f"hash={fixture_hash}")
        label = ", ".join(details) if details else str(fixture)
        lines.append(f"{badge} {label}")
    render_list("Dataset Linkage", lines)


def extract_fixture_refs(data: Any) -> list[dict[str, Any]]:
    fixtures: list[dict[str, Any]] = []
    if not isinstance(data, dict):
        return fixtures
    candidates = [
        data.get("fixtures"),
        data.get("fixture_refs"),
        data.get("datasets"),
        data.get("dataset_fixtures"),
    ]
    for candidate in candidates:
        if isinstance(candidate, list):
            for item in candidate:
                if isinstance(item, dict):
                    fixtures.append(item)
                else:
                    fixtures.append({"id": item})
    return fixtures


def build_fixture_verification(data: Any) -> dict[str, str]:
    verification: dict[str, str] = {}
    if not isinstance(data, dict):
        return verification
    fixtures = data.get("fixtures") or data.get("results") or data.get("cases")
    if not isinstance(fixtures, list):
        return verification
    for fixture in fixtures:
        if not isinstance(fixture, dict):
            continue
        fixture_id = fixture.get("id") or fixture.get("name") or fixture.get("fixture_id")
        fixture_hash = fixture.get("hash") or fixture.get("content_hash")
        status = normalize_verification_status(fixture)
        if fixture_id:
            verification[fixture_id] = status
        if fixture_hash:
            verification[fixture_hash] = status
    return verification


def normalize_verification_status(fixture: dict[str, Any]) -> str:
    if fixture.get("verified") is True:
        return "verified"
    if fixture.get("verified") is False:
        return "mismatch"
    status = fixture.get("status") or fixture.get("verdict") or "unknown"
    status_lower = str(status).lower()
    if "pass" in status_lower or "verified" in status_lower:
        return "verified"
    if "fail" in status_lower or "mismatch" in status_lower:
        return "mismatch"
    return status_lower


def status_to_badge(status: str) -> str:
    normalized = str(status).lower()
    if normalized in {"verified", "pass", "passed", "ok"}:
        return "[verified]"
    if normalized in {"mismatch", "fail", "failed"}:
        return "[mismatch]"
    return "[unknown]"


def extract_pack_ref(data: Any, pack_type: str) -> Optional[dict[str, str]]:
    if not isinstance(data, dict):
        return None
    pack_id_key = f"{pack_type}_pack_id"
    pack_version_key = f"{pack_type}_pack_version"
    if pack_id_key in data or pack_version_key in data:
        pack_id = data.get(pack_id_key)
        pack_version = data.get(pack_version_key)
        if pack_id or pack_version:
            return {"id": str(pack_id) if pack_id is not None else "", "version": str(pack_version) if pack_version is not None else ""}

    pack_key_candidates = [
        f"{pack_type}_pack",
        f"{pack_type}_pack_info",
        f"{pack_type}_pack_metadata",
        f"{pack_type}_pack_meta",
    ]
    for key in pack_key_candidates:
        value = data.get(key)
        if isinstance(value, dict):
            normalized = normalize_pack_ref(value)
            if normalized:
                return normalized
        if isinstance(value, str):
            return {"id": value, "version": ""}
    for nested in data.values():
        if isinstance(nested, dict):
            nested_ref = extract_pack_ref(nested, pack_type)
            if nested_ref:
                return nested_ref
        elif isinstance(nested, list):
            for item in nested:
                if isinstance(item, dict):
                    nested_ref = extract_pack_ref(item, pack_type)
                    if nested_ref:
                        return nested_ref
    return None


def normalize_pack_ref(value: dict[str, Any]) -> Optional[dict[str, str]]:
    pack_id = value.get("id") or value.get("pack_id") or value.get("identifier")
    pack_version = value.get("version") or value.get("pack_version") or value.get("ver")
    if pack_id or pack_version:
        return {
            "id": str(pack_id) if pack_id is not None else "",
            "version": str(pack_version) if pack_version is not None else "",
        }
    return None


def format_pack_label(pack_ref: Optional[dict[str, str]]) -> Optional[str]:
    if not pack_ref:
        return None
    pack_id = pack_ref.get("id")
    pack_version = pack_ref.get("version")
    if pack_id and pack_version:
        return f"{pack_id}@{pack_version}"
    if pack_id:
        return str(pack_id)
    if pack_version:
        return str(pack_version)
    return None


def format_panel_title(title: str, data: Any) -> str:
    if "Reasoning (CogA)" in title:
        label = format_pack_label(extract_pack_ref(data, "reasoning"))
        if label:
            return f"{title} [pack: {label}]"
    if "Build (cA)" in title:
        label = format_pack_label(extract_pack_ref(data, "policy"))
        if label:
            return f"{title} [pack: {label}]"
    return title


def render_panel(
    title: str,
    path: Path,
    context: ViewerContext,
    extra_renderer: Callable[[Any, ViewerContext], None] | None = None,
) -> None:
    if path.is_file():
        data = load_json(path)
        render_section(format_panel_title(title, data), data)
        if extra_renderer:
            extra_renderer(data, context)
    else:
        render_missing(title, path)


def render_from_directory(directory: Path) -> None:
    context = build_context(directory)
    renderers: dict[str, Callable[[Any, ViewerContext], None]] = {
        "Reasoning (CogA)": lambda data, _: render_coga_extras(data),
        "Build (cA)": lambda data, _: render_build_extras(data),
        "Execution Receipt": lambda data, ctx: render_receipt_extras_with_context(data, ctx),
        "Execution Receipt (System)": lambda data, _: render_receipt_extras(data),
        "Replay Report": lambda data, _: render_replay_report_extras(data),
        "Acceptance Report": lambda data, _: render_acceptance_report(data),
        "Harness Report": lambda data, _: render_harness_report(data),
    }
    for title, filename in PANEL_FILES:
        path = directory / filename
        render_panel(title, path, context, renderers.get(title))

    render_raw_json_panels(directory)


def render_receipt_extras_with_context(data: Any, context: ViewerContext) -> None:
    render_receipt_extras(data)
    replay_report = context.get("replay_report.json")
    if replay_report is not None:
        render_dataset_linkage(data, replay_report)


def build_context(directory: Path) -> ViewerContext:
    data_by_filename: dict[str, Any] = {}
    for filename in KNOWN_JSON_FILES:
        path = directory / filename
        if path.is_file():
            data_by_filename[filename] = load_json(path)
    return ViewerContext(directory=directory, data_by_filename=data_by_filename)


def render_raw_json_panels(directory: Path) -> None:
    extra_files = sorted(
        [
            path
            for path in directory.glob("*.json")
            if path.name not in KNOWN_JSON_FILES
        ]
    )
    for path in extra_files:
        data = load_json(path)
        render_section(f"Raw JSON: {path.name}", data)


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
