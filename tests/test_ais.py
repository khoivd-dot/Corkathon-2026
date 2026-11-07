"""AIS counts: off by default, aggregate only, never names or positions."""
import os
import unittest
from unittest import mock

from corkathon import server
from corkathon.sources import ais

PAYLOAD = [{"ERROR": False, "RECORDS": 4},
           [{"MMSI": 1, "NAME": "SECRET ONE", "NAVSTAT": 1, "SOG": 0, "LATITUDE": 51.9, "LONGITUDE": 4.1},
            {"MMSI": 2, "NAME": "SECRET TWO", "NAVSTAT": 1, "SOG": 2},
            {"MMSI": 3, "NAME": "SECRET THREE", "NAVSTAT": 0, "SOG": 140},
            {"MMSI": 4, "NAME": "SECRET FOUR", "NAVSTAT": 5, "SOG": 0}]]


class AisTests(unittest.TestCase):
    def test_off_by_default(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertFalse(ais.ais_enabled())
        with mock.patch.dict(os.environ, {"AIS_ENABLED": "1"}, clear=True):
            self.assertFalse(ais.ais_enabled())  # needs a username too

    def test_parse_keeps_counts_only(self):
        recs, _, _ = ais.AisPortLoader("Rotterdam", 51.95, 4.14).parse(PAYLOAD)
        self.assertEqual({k: recs[0][k] for k in ("waiting", "moored", "moving")}, {"waiting": 2, "moored": 1, "moving": 1})
        self.assertNotIn("SECRET", repr(recs))

    def test_answer_has_no_ais_when_off(self):
        form = {"importer": "X Ltd", "origin_port": "Santos", "destination_port": "Cork", "currency": "USD",
                "fixed_rate_share": "none", "stock_days": "21", "lead_time_days": "35",
                "window_start": "2026-10-24", "window_end": "2026-11-07"}
        with mock.patch.dict(os.environ, {"SNAPSHOT_ONLY": "1", "AIS_ENABLED": "0"}):
            self.assertNotIn("ais", server.answer(form))

    def test_counts_live_without_names(self):
        env = {"AIS_ENABLED": "1", "AISHUB_USERNAME": "t", "SNAPSHOT_ONLY": "0", "SNAPSHOT": "0",
               "CACHE_DIR": "/nonexistent-cache"}
        with mock.patch.dict(os.environ, env), \
             mock.patch.object(ais, "http_json", return_value=PAYLOAD), \
             mock.patch.object(ais.GATE, "acquire", return_value=True), \
             mock.patch.object(ais.AisPortLoader, "write_cache"):
            out = server.ais_counts(["Rotterdam"])
        self.assertEqual(out["ports"], [{"port": "Rotterdam", "waiting": 2, "moored": 1, "moving": 1}])
        self.assertEqual(out["mode"], "live")
        self.assertNotIn("SECRET", repr(out))

if __name__ == "__main__":
    unittest.main()
