"""Every view's data comes from a real BLUX tool, called with a fixed argument list and parsed as the one JSON
document that tool prints. Nothing here re-implements BLUX logic: routing, policy, graphs and verification
are whatever the tools report. A tool that is missing or fails yields an explicit error document, never a
guessed value.

Output is passed through BLUX's own redaction before it leaves the process.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:  # BLUX's redaction (SDK credential patterns plus secret-named values), when BLUX is installed
    from blux_runtime.security.environment import redact as _redact
except ImportError:  # pragma: no cover - the app still runs without BLUX installed, with a conservative fallback
    import re

    _SECRETISH = re.compile(r"(?i)((?:token|secret|password|api[_-]?key)\S*\s*[:=]\s*)\S+|\b(?:sk-|ghp_|xox[bp]-)\S+")

    def _redact(text: str) -> str:
        return _SECRETISH.sub(lambda m: (m.group(1) or "") + "[redacted]", text)


TIMEOUT = 60


@dataclass
class Tools:
    """Where each tool lives. Resolved once to absolute paths, so shell functions or aliases that shadow a name
    (for example a `blux` function in a startup file) can never be picked up."""

    blux: str | None = None
    system: str | None = None
    god: list[str] | None = None
    voidforge: str | None = None
    store: Path | None = None
    roots: list[Path] = field(default_factory=list)
    evals_report: Path | None = None
    datasets: list[Path] = field(default_factory=list)

    @classmethod
    def discover(cls, **overrides: Any) -> Tools:
        def which(name: str, env: str) -> str | None:
            value = os.environ.get(env) or shutil.which(name)
            return str(Path(value).resolve()) if value else None

        god = os.environ.get("BLUX_APP_GOD")
        tools = cls(
            blux=which("blux", "BLUX_APP_BLUX"),
            system=which("blux-system", "BLUX_APP_SYSTEM"),
            god=god.split() if god else ([str(Path(g).resolve())] if (g := shutil.which("god")) else None),
            voidforge=which("voidforge", "BLUX_APP_VOIDFORGE"),
        )
        for k, v in overrides.items():
            if v is not None:
                setattr(tools, k, v)
        return tools


def scrub(value: Any) -> Any:
    if isinstance(value, str):
        return _redact(value)
    if isinstance(value, dict):
        return {k: scrub(v) for k, v in value.items()}
    if isinstance(value, list):
        return [scrub(v) for v in value]
    return value


def call(argv: list[str] | None, *extra: str, env: dict[str, str] | None = None) -> dict[str, Any]:
    """Run a tool; return {"ok": True, "data": doc} or {"ok": False, "error": ...}. Never raises."""
    if not argv:
        return {"ok": False, "error": "tool not installed"}
    cmd = [*argv, *extra]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT, check=False, env=env)  # noqa: S603
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "error": f"{Path(cmd[0]).name}: {type(exc).__name__}"}
    try:
        doc = json.loads(proc.stdout) if proc.stdout.strip() else None
    except ValueError:
        doc = None
    if proc.returncode != 0 or doc is None:
        detail = doc if doc is not None else (proc.stderr.strip().splitlines() or ["no output"])[-1][:300]
        return scrub({"ok": False, "exit_code": proc.returncode, "error": detail})
    return {"ok": True, "data": scrub(doc)}


def read_json(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {"ok": False, "error": "not configured"}
    try:
        return {"ok": True, "data": scrub(json.loads(path.read_text(encoding="utf-8")))}
    except (OSError, ValueError) as exc:
        return {"ok": False, "error": f"{path.name}: {type(exc).__name__}"}


# --- views ------------------------------------------------------------------------------------------------

def _store(t: Tools) -> list[str]:
    return ["--store", str(t.store)] if t.store else []


def overview(t: Tools) -> dict[str, Any]:
    return {"blux": call([t.blux] if t.blux else None, "version"), "system": call([t.system] if t.system else None, "version"),
            "store": str(t.store) if t.store else None,
            "tools": {"blux": bool(t.blux), "blux-system": bool(t.system), "god": bool(t.god), "voidforge": bool(t.voidforge)}}


def projects(t: Tools) -> dict[str, Any]:
    roots = [a for r in t.roots for a in ("--root", str(r))]
    return call(t.god, "index", *roots, "--json")


def capabilities(t: Tools) -> dict[str, Any]:
    return call([t.blux] if t.blux else None, "capabilities")


def models(t: Tools) -> dict[str, Any]:
    # The catalog lists logical models and what their routes provide; it never contains credentials.
    return call([t.blux] if t.blux else None, "models")


def operations(t: Tools) -> dict[str, Any]:
    if not t.store:
        return {"ok": False, "error": "no BLUX System store configured (--store)"}
    return call([t.system] if t.system else None, "list", *_store(t))


def operation(t: Tools, operation_id: str) -> dict[str, Any]:
    if not t.store:
        return {"ok": False, "error": "no BLUX System store configured (--store)"}
    sys_ = [t.system] if t.system else None
    return {"show": call(sys_, "show", "--operation", operation_id, *_store(t)),
            "graph": call(sys_, "graph", "--root", operation_id, *_store(t)),
            "timeline": call(sys_, "timeline", "--operation", operation_id, *_store(t))}


def session(t: Tools, session_id: str) -> dict[str, Any]:
    if not t.store:
        return {"ok": False, "error": "no BLUX System store configured (--store)"}
    sys_ = [t.system] if t.system else None
    return {"receipts": call(sys_, "list", "--session", session_id, *_store(t)),
            "graph": call(sys_, "graph", "--session", session_id, *_store(t))}


def timeline(t: Tools) -> dict[str, Any]:
    if not t.store:
        return {"ok": False, "error": "no BLUX System store configured (--store)"}
    return call([t.system] if t.system else None, "timeline", *_store(t))


def devices(t: Tools) -> dict[str, Any]:
    # Read-only device listing only. VoidForge authorizes every write on the device itself; the app exposes none.
    return call([t.voidforge] if t.voidforge else None, "devices")


def evals(t: Tools) -> dict[str, Any]:
    return read_json(t.evals_report)


def training(t: Tools) -> dict[str, Any]:
    return {"datasets": [{"path": d.name, **read_json(d / "manifest.json")} for d in t.datasets]}


# --- the only controls: read-only checks run by BLUX System --------------------------------------------------

CONTROLS = {
    "verify-store": lambda t, arg: call([t.system] if t.system else None, "verify", *_store(t)),
    "replay-check": lambda t, arg: call([t.system] if t.system else None, "replay-check", arg, *_store(t)),
}
