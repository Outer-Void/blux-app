"""Local HTTP server: one page plus a JSON API over `sources`. Bound to 127.0.0.1 only.

Security: requests must name this server as Host (blocks DNS rebinding), POST controls need the per-launch
token from the page and a same-origin request, identifiers are validated before they reach any tool, and
every response forbids framing, sniffing and caching.
"""

from __future__ import annotations

import json
import re
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from typing import Any
from urllib.parse import urlsplit

from blux_app import VERSION, sources

OPERATION_ID = re.compile(r"^op_[0-9A-HJKMNP-TV-Z]{26}$")
SESSION_ID = re.compile(r"^ses_[0-9A-HJKMNP-TV-Z]{26}$")
STATIC = {"/": ("index.html", "text/html; charset=utf-8"), "/app.js": ("app.js", "text/javascript; charset=utf-8"),
          "/app.css": ("app.css", "text/css; charset=utf-8")}
VIEWS = {
    "overview": sources.overview, "projects": sources.projects, "capabilities": sources.capabilities,
    "models": sources.models, "operations": sources.operations, "timeline": sources.timeline,
    "devices": sources.devices, "evals": sources.evals, "training": sources.training,
}
HEADERS = {
    "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; "
                               "frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
    "X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY", "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store", "Cross-Origin-Opener-Policy": "same-origin",
}


class App:
    def __init__(self, tools: sources.Tools) -> None:
        self.tools = tools
        self.token = secrets.token_urlsafe(32)


def make_handler(app: App, port_box: list[int]) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = f"blux-app/{VERSION}"
        sys_version = ""

        def log_message(self, format: str, *args: Any) -> None:
            return  # no request logging: paths can contain identifiers

        def _allowed_host(self) -> bool:
            host = self.headers.get("Host", "")
            return host in (f"127.0.0.1:{port_box[0]}", f"localhost:{port_box[0]}")

        def _send(self, status: int, body: bytes, ctype: str) -> None:
            self.send_response(status)
            for k, v in HEADERS.items():
                self.send_header(k, v)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _json(self, status: int, doc: Any) -> None:
            self._send(status, json.dumps(doc, sort_keys=True).encode(), "application/json")

        def do_GET(self) -> None:
            if not self._allowed_host():
                return self._json(403, {"error": "unexpected Host header"})
            path = urlsplit(self.path).path
            if path in STATIC:
                name, ctype = STATIC[path]
                body = resources.files("blux_app").joinpath(f"static/{name}").read_text(encoding="utf-8")
                if name == "index.html":
                    body = body.replace("__TOKEN__", app.token).replace("__VERSION__", VERSION)
                return self._send(200, body.encode(), ctype)
            parts = path.strip("/").split("/")
            if len(parts) == 2 and parts[0] == "api" and parts[1] in VIEWS:
                return self._json(200, VIEWS[parts[1]](app.tools))
            if len(parts) == 3 and parts[:2] == ["api", "operation"]:
                if not OPERATION_ID.match(parts[2]):
                    return self._json(400, {"error": "not an operation id"})
                return self._json(200, sources.operation(app.tools, parts[2]))
            if len(parts) == 3 and parts[:2] == ["api", "session"]:
                if not SESSION_ID.match(parts[2]):
                    return self._json(400, {"error": "not a session id"})
                return self._json(200, sources.session(app.tools, parts[2]))
            return self._json(404, {"error": "not found"})

        def do_POST(self) -> None:
            if not self._allowed_host():
                return self._json(403, {"error": "unexpected Host header"})
            origin = self.headers.get("Origin")
            if origin and origin not in (f"http://127.0.0.1:{port_box[0]}", f"http://localhost:{port_box[0]}"):
                return self._json(403, {"error": "cross-origin request refused"})
            if not secrets.compare_digest(self.headers.get("X-BLUX-App-Token", ""), app.token):
                return self._json(403, {"error": "missing or wrong control token"})
            parts = urlsplit(self.path).path.strip("/").split("/")
            if len(parts) < 3 or parts[:2] != ["api", "control"] or parts[2] not in sources.CONTROLS:
                return self._json(404, {"error": "no such control"})
            arg = parts[3] if len(parts) > 3 else ""
            if parts[2] == "replay-check" and not OPERATION_ID.match(arg):
                return self._json(400, {"error": "not an operation id"})
            return self._json(200, sources.CONTROLS[parts[2]](app.tools, arg))

        def do_PUT(self) -> None:
            self._json(405, {"error": "method not allowed"})

        do_DELETE = do_PATCH = do_PUT

    return Handler


def serve(tools: sources.Tools, port: int = 0) -> tuple[ThreadingHTTPServer, App, threading.Thread]:
    """Start in a background thread; return (server, app, thread). Port 0 picks a free port."""
    app = App(tools)
    port_box = [port]
    httpd = ThreadingHTTPServer(("127.0.0.1", port), make_handler(app, port_box))
    port_box[0] = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd, app, thread
