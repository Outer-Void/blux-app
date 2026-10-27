"""blux-app serve|snapshot|legacy-view. Exit codes: 0 ok, 2 usage."""

from __future__ import annotations

import argparse
import json
import sys
import time
import webbrowser
from pathlib import Path

from blux_app import VERSION, server, sources


def tools_from(args: argparse.Namespace) -> sources.Tools:
    return sources.Tools.discover(store=args.store, roots=args.root or [], evals_report=args.evals_report, datasets=args.dataset or [])


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="blux-app", description="BLUX mission control (local, read-only).")
    p.add_argument("--version", action="version", version=f"blux-app {VERSION}")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("serve", "snapshot"):
        s = sub.add_parser(name)
        s.add_argument("--store", type=Path, help="BLUX System store to inspect")
        s.add_argument("--root", type=Path, action="append", help="workspace root for GOD project discovery (repeatable)")
        s.add_argument("--evals-report", type=Path, help="evals/reports/gen0/report.json")
        s.add_argument("--dataset", type=Path, action="append", help="a blux_training dataset directory (repeatable)")
        if name == "serve":
            s.add_argument("--port", type=int, default=0)
            s.add_argument("--open", action="store_true", help="open the page in a browser")
    lv = sub.add_parser("legacy-view", help="the BLUX App 1.0 viewer for pre-contract run directories")
    lv.add_argument("--root", type=Path, required=True)
    args = p.parse_args(argv)

    if args.cmd == "legacy-view":
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "legacy"))
        from blux_view import render_from_directory  # type: ignore[import-not-found]

        render_from_directory(args.root.expanduser().resolve())
        return 0
    tools = tools_from(args)
    if args.cmd == "snapshot":
        doc = {name: fn(tools) for name, fn in server.VIEWS.items()}
        print(json.dumps(doc, indent=1, sort_keys=True))
        return 0
    httpd, _app, _thread = server.serve(tools, args.port)
    url = f"http://127.0.0.1:{httpd.server_address[1]}/"
    print(f"BLUX Mission Control on {url}  (Ctrl-C to stop)", flush=True)
    if args.open:
        webbrowser.open(url)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        httpd.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
