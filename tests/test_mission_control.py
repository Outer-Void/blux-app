"""BLUX App 2.0 against the real tools: a real BLUX System store, real `blux run` operations, real HTTP.

Needs `blux` and `blux-system` on PATH (or BLUX_APP_BLUX / BLUX_APP_SYSTEM); the end-to-end tests skip
without them, the security tests always run.
"""

from __future__ import annotations

import http.client
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from blux_app import server, sources

BLUX = os.environ.get("BLUX_APP_BLUX") or shutil.which("blux")
SYSTEM = os.environ.get("BLUX_APP_SYSTEM") or shutil.which("blux-system")


def request(port: int, method: str, path: str, headers: dict[str, str] | None = None) -> tuple[int, dict, dict[str, str]]:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=60)
    conn.request(method, path, headers={"Host": f"127.0.0.1:{port}", **(headers or {})})
    resp = conn.getresponse()
    body = resp.read()
    hdrs = {k: v for k, v in resp.getheaders()}
    conn.close()
    try:
        return resp.status, json.loads(body), hdrs
    except ValueError:
        return resp.status, {"_text": body.decode()}, hdrs


class Base(unittest.TestCase):
    tools: sources.Tools

    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = Path(tempfile.mkdtemp(prefix="blux-app-"))
        cls.store = cls.tmp / "truth"
        cls.tools = sources.Tools.discover(store=cls.store)
        cls.httpd, cls.app, _ = server.serve(cls.tools)
        cls.port = cls.httpd.server_address[1]

    @classmethod
    def tearDownClass(cls) -> None:
        cls.httpd.shutdown()
        shutil.rmtree(cls.tmp, ignore_errors=True)


class SecurityTest(Base):
    def test_wrong_host_is_refused(self) -> None:
        for host in ("evil.example", f"127.0.0.1:{self.port + 1}", ""):
            conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
            conn.putrequest("GET", "/api/overview", skip_host=True)
            if host:
                conn.putheader("Host", host)
            conn.endheaders()
            self.assertEqual(conn.getresponse().status, 403, host)
            conn.close()

    def test_controls_need_the_token_and_same_origin(self) -> None:
        self.assertEqual(request(self.port, "POST", "/api/control/verify-store")[0], 403)
        self.assertEqual(request(self.port, "POST", "/api/control/verify-store", {"X-BLUX-App-Token": "nope"})[0], 403)
        token = {"X-BLUX-App-Token": self.app.token}
        self.assertEqual(request(self.port, "POST", "/api/control/verify-store", {**token, "Origin": "http://evil.example"})[0], 403)
        self.assertEqual(request(self.port, "POST", "/api/control/rm-everything", token)[0], 404)  # only listed controls exist
        self.assertEqual(request(self.port, "POST", "/api/control/replay-check/--store=/etc", token)[0], 400)

    def test_identifiers_are_validated_before_any_tool_runs(self) -> None:
        for path in ("/api/operation/--help", "/api/operation/op_bad", "/api/session/ses_x;rm"):
            self.assertEqual(request(self.port, "GET", path)[0], 400, path)

    def test_other_methods_and_unknown_paths(self) -> None:
        self.assertEqual(request(self.port, "DELETE", "/api/operations")[0], 405)
        self.assertEqual(request(self.port, "GET", "/api/nope")[0], 404)

    def test_page_headers_and_token_embedding(self) -> None:
        status, body, hdrs = request(self.port, "GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(self.app.token, body["_text"])
        self.assertIn("frame-ancestors 'none'", hdrs["Content-Security-Policy"])
        self.assertEqual(hdrs["Cache-Control"], "no-store")
        self.assertNotIn("innerHTML", request(self.port, "GET", "/app.js")[1]["_text"])  # untrusted text never becomes markup

    def test_missing_tools_are_explicit_errors(self) -> None:
        bare = sources.Tools()
        self.assertEqual(sources.capabilities(bare), {"ok": False, "error": "tool not installed"})
        self.assertFalse(sources.operations(bare)["ok"])

    def test_secrets_are_redacted(self) -> None:
        self.assertNotIn("sk-abcdefabcdefabcdefabcdefabcdefabcdef", json.dumps(sources.scrub({"x": "key sk-abcdefabcdefabcdefabcdefabcdefabcdef"})))
        self.assertIn("[redacted]", sources.scrub("api_key = hunter22hunter22"))


@unittest.skipUnless(BLUX and SYSTEM, "blux and blux-system are needed for the end-to-end test")
class EndToEndTest(Base):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        env = {**os.environ, "OPENAI_API_KEY": "sk-test-0123456789abcdef0123456789abcdef"}  # must never reach a response
        subprocess.run([SYSTEM, "init", "--store", str(cls.store)], check=True, capture_output=True)
        cls.session = json.loads(subprocess.run([BLUX, "id", "session"], check=True, capture_output=True, text=True).stdout)["id"]
        parent = json.loads(subprocess.run([BLUX, "run", "echo.test", "--input", '{"message":"parent"}', "--session-id", cls.session,
                                            "--system-store", str(cls.store)],
                                           check=True, capture_output=True, text=True, env=env).stdout)
        cls.parent_op = parent["operation_id"]
        child = json.loads(subprocess.run([BLUX, "run", "echo.test", "--input", '{"message":"child"}', "--actor-type", "agent",
                                           "--actor-id", "eval-agent", "--parent-operation-id", cls.parent_op, "--session-id", cls.session,
                                           "--system-store", str(cls.store)],
                                          check=True, capture_output=True, text=True, env=env).stdout)
        cls.child_op = child["operation_id"]

    def test_inspects_a_real_end_to_end_operation(self) -> None:
        status, ops, _ = request(self.port, "GET", "/api/operations")
        self.assertEqual(status, 200)
        self.assertTrue(ops["ok"])
        receipts = {r["operation_id"]: r for r in ops["data"]["receipts"]}
        self.assertEqual(set(receipts), {self.parent_op, self.child_op})
        self.assertEqual(receipts[self.child_op]["parent_operation_id"], self.parent_op)
        status, detail, _ = request(self.port, "GET", f"/api/operation/{self.parent_op}")
        self.assertEqual(status, 200)
        self.assertTrue(detail["show"]["ok"] and detail["graph"]["ok"] and detail["timeline"]["ok"])
        graph = detail["graph"]["data"]
        self.assertIn(self.child_op, graph["nodes"])  # the subagent operation hangs under its parent
        self.assertEqual(graph["nodes"][self.parent_op]["aggregate_status"], "SUCCESS")

    def test_session_and_real_catalogs(self) -> None:
        status, body, _ = request(self.port, "GET", f"/api/session/{self.session}")
        self.assertEqual(status, 200)
        self.assertTrue(body["receipts"]["ok"])
        self.assertEqual(body["receipts"]["data"]["count"], 2)
        for view in ("capabilities", "models", "overview", "timeline"):
            status, body, _ = request(self.port, "GET", f"/api/{view}")
            self.assertEqual(status, 200, view)
            self.assertNotIn("sk-test-0123456789abcdef", json.dumps(body), view)
        caps = request(self.port, "GET", "/api/capabilities")[1]
        self.assertTrue(caps["ok"])
        self.assertIn("echo.test", json.dumps(caps["data"]))

    def test_authorized_controls_are_read_only_checks(self) -> None:
        token = {"X-BLUX-App-Token": self.app.token}
        status, body, _ = request(self.port, "POST", "/api/control/verify-store", token)
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"] and body["data"]["ok"])
        before = sorted(p.name for p in self.store.rglob("*"))
        status, body, _ = request(self.port, "POST", f"/api/control/replay-check/{self.parent_op}", token)
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertEqual(sorted(p.name for p in self.store.rglob("*")), before)  # checks change nothing in the store


if __name__ == "__main__":
    unittest.main()
