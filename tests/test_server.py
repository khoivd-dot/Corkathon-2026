import json
import os
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

from corkathon import server

FORM = {"importer": "Secret Importer Ltd", "origin_port": "Santos", "destination_port": "Cork",
        "transshipment_ports": "Rotterdam", "currency": "USD", "fixed_rate_share": "none",
        "stock_days": "21", "lead_time_days": "35", "window_start": "2026-10-24", "window_end": "2026-11-07"}


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.env = mock.patch.dict(os.environ, {"SNAPSHOT_ONLY": "1"})
        cls.env.start()
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        cls.base = f"http://127.0.0.1:{cls.httpd.server_port}"
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown(); cls.env.stop()

    def test_healthz(self):
        with urllib.request.urlopen(self.base + "/healthz") as r:
            self.assertEqual(r.read(), b"ok")
            self.assertEqual(r.headers["X-Content-Type-Options"], "nosniff")

    def test_answer_offline_and_nothing_written(self):
        cache = Path(os.environ.get("CACHE_DIR", ".cache"))
        before = {p: p.read_bytes() for p in cache.glob("*")} if cache.exists() else {}
        req = urllib.request.Request(self.base + "/api/answer", json.dumps(FORM).encode(),
                                     {"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as r:
            out = json.loads(r.read())
        self.assertIn(out["state"], ("alert", "covered", "insufficient"))
        after = {p: p.read_bytes() for p in cache.glob("*")} if cache.exists() else {}
        self.assertEqual(before, after)
        self.assertFalse(any(b"Secret Importer" in v for v in after.values()))

    def test_bad_input_400(self):
        req = urllib.request.Request(self.base + "/api/answer", b"{}", {"Content-Type": "application/json"})
        with self.assertRaises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(req)
        self.assertEqual(e.exception.code, 400)

    def test_no_path_traversal(self):
        with self.assertRaises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(self.base + "/../render.yaml")
        self.assertEqual(e.exception.code, 404)

    def test_render_yaml_rules(self):
        y = (Path(__file__).parents[1] / "render.yaml").read_text()
        for s in ('plan: starter', 'autoDeployTrigger: "off"', "healthCheckPath: /healthz",
                  "sizeGB: 1", "key: CACHE_DIR", 'value: "1800"'):
            self.assertIn(s, y)
        self.assertNotIn("sync: false", y)  # no secrets


if __name__ == "__main__":
    unittest.main()
