"""GDELT spacing and which typed ports may reach GDELT or the cache."""
import os
import unittest
from unittest import mock

from corkathon import server
from corkathon.sources import gdelt
from corkathon.sources.gdelt import RateGate


class FakeClock:
    def __init__(self):
        self.t = 100.0
        self.slept = []

    def __call__(self):
        return self.t

    def sleep(self, s):
        self.slept.append(round(s, 2))
        self.t += s


class RateGateTests(unittest.TestCase):
    def test_spaces_calls_and_refuses_when_wait_too_long(self):
        c = FakeClock()
        g = RateGate(interval_s=5.5, clock=c, sleep=c.sleep)
        self.assertTrue(g.acquire(6))          # first call: no wait
        self.assertTrue(g.acquire(6))          # second call waits 5.5 s
        self.assertEqual(c.slept, [5.5])
        self.assertFalse(g.acquire(1))         # would need 5.5 s, budget 1 s
        c.t += 10
        self.assertTrue(g.acquire(0))          # slot free again


class NewsPortsTests(unittest.TestCase):
    def test_known_ports_are_canonical_and_deduplicated(self):
        known, unknown = server.news_ports(["santos", "Cork (Ringaskiddy)", "CORK", "Atlantis Quay"])
        self.assertEqual(known, ["Santos", "Cork"])
        self.assertEqual(unknown, ["Atlantis Quay"])

    def test_unknown_port_never_reaches_gdelt(self):
        seen = []
        real = server.PortGdeltLoader

        def spy(port, **kw):
            seen.append(port)
            return real(port, **kw)

        form = {"importer": "X Ltd", "origin_port": "Atlantis Quay", "destination_port": "cork",
                "currency": "USD", "fixed_rate_share": "none", "stock_days": "21",
                "lead_time_days": "35", "window_start": "2026-10-24", "window_end": "2026-11-07"}
        with mock.patch.dict(os.environ, {"SNAPSHOT_ONLY": "1"}), mock.patch.object(server, "PortGdeltLoader", spy):
            out = server.answer(form)
        self.assertEqual(seen, ["Cork"])
        self.assertEqual(out["news_ports"]["unknown"], ["Atlantis Quay"])
        self.assertEqual([p["port"] for p in out["news_ports"]["checked"]], ["Cork"])

    def test_busy_gate_falls_back_instead_of_calling(self):
        with mock.patch.object(gdelt.GATE, "acquire", return_value=False), \
             mock.patch.object(gdelt, "http_get") as get:
            res = gdelt.PortGdeltLoader("Cork", gate_wait_s=0).load_live()
        get.assert_not_called()
        self.assertEqual(res.status, "unavailable")
        self.assertIn("busy", res.reason)


class OfficialQueryTests(unittest.TestCase):
    def test_official_query_only_with_confirmation_on(self):
        with mock.patch.dict(os.environ, {"CONFIRMATION_ENABLED": "0"}):
            off = gdelt.PortGdeltLoader("Rotterdam")
        with mock.patch.dict(os.environ, {"CONFIRMATION_ENABLED": "1"}):
            on = gdelt.PortGdeltLoader("Rotterdam")
        self.assertEqual(list(off.queries), ["rotterdam"])
        self.assertEqual(list(on.queries), ["rotterdam", "rotterdam-official"])
        self.assertIn("domain:portofrotterdam.com", on.queries["rotterdam-official"])
        self.assertNotEqual(off.cache_key(), on.cache_key())


if __name__ == "__main__":
    unittest.main()
