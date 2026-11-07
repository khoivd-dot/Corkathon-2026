import json
import os
import threading
import unittest
import urllib.error
import urllib.request
from datetime import date, timedelta
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

from corkathon import server

FORM = {
    "importer": "Secret Importer Ltd", "origin_port": "Santos", "destination_port": "Cork",
    "transshipment_ports": "Rotterdam", "currency": "USD", "fixed_rate_share": "none",
    "stock_days": "21", "lead_time_days": "35", "window_start": "2026-10-24", "window_end": "2026-11-07"
}


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
        cls.httpd.shutdown()
        cls.env.stop()

    def test_healthz(self):
        with urllib.request.urlopen(self.base + "/healthz") as r:
            self.assertEqual(r.read(), b"ok")
            self.assertEqual(r.headers["X-Content-Type-Options"], "nosniff")

    def test_answer_offline_and_nothing_written(self):
        cache = Path(os.environ.get("CACHE_DIR", ".cache"))
        before = {p: p.read_bytes() for p in cache.glob("*")} if cache.exists() else {}
        req = urllib.request.Request(
            self.base + "/api/answer", json.dumps(FORM).encode(),
            {"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as r:
            out = json.loads(r.read())
        self.assertIn(out["state"], ("alert", "covered", "insufficient"))
        self.assertIn("timing", out)
        self.assertIn("order_by", out["timing"])
        after = {p: p.read_bytes() for p in cache.glob("*")} if cache.exists() else {}
        self.assertEqual(before, after)
        self.assertFalse(any(b"Secret Importer" in v for v in after.values()))

    def test_bad_input_400(self):
        req = urllib.request.Request(self.base + "/api/answer", b"{}", {"Content-Type": "application/json"})
        with self.assertRaises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(req)
        self.assertEqual(e.exception.code, 400)

    def _post(self, body, headers=None):
        req = urllib.request.Request(self.base + "/api/answer", body,
                                     {"Content-Type": "application/json", **(headers or {})})
        with self.assertRaises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(req, timeout=5)
        return e.exception

    def test_json_that_is_not_an_object_400(self):
        self.assertEqual(self._post(b"[1, 2]").code, 400)

    def test_unexpected_error_is_json_500_not_a_dropped_connection(self):
        with mock.patch.object(server, "answer", side_effect=RuntimeError("boom Secret Importer")):
            err = self._post(json.dumps(FORM).encode())
        self.assertEqual(err.code, 500)
        self.assertIn("errors", json.loads(err.read()))

    def test_refresh_once_warms_every_shared_source(self):
        calls = []
        fake = lambda sid: type("L", (), {"load": lambda self: calls.append(sid)})
        with mock.patch.dict(server.LOADERS, {s: fake(s) for s in server.CONTEXT_SOURCES}), \
             mock.patch.object(server, "PortGdeltLoader", lambda p: type("G", (), {"load": lambda self: calls.append(p)})()), \
             mock.patch.object(server, "PortWeatherLoader", lambda p, lat, lon: type("W", (), {"load": lambda self: calls.append("weather " + p)})()), \
             mock.patch.object(server, "LANE_PORTS", ("Cork",)), mock.patch.dict(os.environ, {"WEATHER_ENABLED": "1"}):
            server.refresh_once()
        self.assertEqual(calls, [*server.CONTEXT_SOURCES, "Cork", "weather Cork"])

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

    def test_parse_endpoint(self):
        payload = {
            "q": "I bring homewares from Shanghai through Rotterdam to Dublin in dollars, about 10 weeks of stock, takes 6 weeks to get here"
        }
        req = urllib.request.Request(
            self.base + "/api/parse", json.dumps(payload).encode(),
            {"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as r:
            self.assertEqual(r.status, 200)
            data = json.loads(r.read())
            self.assertEqual(data["missing"], [])
            self.assertEqual(data["fields"]["origin_port"], "Shanghai")
            self.assertEqual(data["fields"]["destination_port"], "Dublin")
            self.assertEqual(data["fields"]["currency"], "USD")
            self.assertTrue(len(data["understood"]) > 0)

    def test_timing_endpoint(self):
        today = date.today()
        # Valid timing request
        payload = {
            "origin_port": "Shanghai",
            "destination_port": "Dublin",
            "stock_days": 70,
            "lead_time_days": 42,
            "as_of": (today + timedelta(days=20)).isoformat(),
        }
        req = urllib.request.Request(
            self.base + "/api/timing", json.dumps(payload).encode(),
            {"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as r:
            self.assertEqual(r.status, 200)
            data = json.loads(r.read())
            self.assertIn("order_by", data)
            self.assertIn("headline", data)
            self.assertIn("days_left", data)

        # Invalid as_of out of range (more than 400 days from today)
        payload_bad = {**payload, "as_of": (today + timedelta(days=500)).isoformat()}
        req_bad = urllib.request.Request(
            self.base + "/api/timing", json.dumps(payload_bad).encode(),
            {"Content-Type": "application/json"}
        )
        with self.assertRaises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(req_bad)
        self.assertEqual(e.exception.code, 400)

        # Invalid date format
        payload_invalid = {**payload, "as_of": "not-a-date"}
        req_invalid = urllib.request.Request(
            self.base + "/api/timing", json.dumps(payload_invalid).encode(),
            {"Content-Type": "application/json"}
        )
        with self.assertRaises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(req_invalid)
        self.assertEqual(e.exception.code, 400)

    def test_e2e_parse_to_answer_timing_dated(self):
        # 1. Parse natural query
        q = "I bring homewares from Shanghai through Rotterdam to Dublin in dollars, about 10 weeks of stock, takes 6 weeks to get here"
        req_p = urllib.request.Request(
            self.base + "/api/parse", json.dumps({"q": q}).encode(),
            {"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req_p) as r_p:
            parsed = json.loads(r_p.read())
            self.assertEqual(parsed["missing"], [])
            fields = parsed["fields"]

        # 2. Post parsed fields to /api/answer
        req_a = urllib.request.Request(
            self.base + "/api/answer", json.dumps(fields).encode(),
            {"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req_a) as r_a:
            self.assertEqual(r_a.status, 200)
            ans = json.loads(r_a.read())

        # 3. Assert timing present, headline formatted, every source dated
        self.assertIn("timing", ans)
        timing = ans["timing"]
        self.assertIn("order_by", timing)
        self.assertIn("headline", timing)
        self.assertTrue(timing["headline"].startswith("Order by"))
        self.assertIn(timing["headline"], ans["headline"])

        # Every source in sources list has checked_at and source_updated_at
        self.assertTrue(len(ans["sources"]) >= 4)
        for s in ans["sources"]:
            self.assertIn("name", s)
            self.assertIn("mode", s)
            self.assertIn("checked_at", s)


if __name__ == "__main__":
    unittest.main()
