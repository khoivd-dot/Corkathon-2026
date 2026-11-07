"""Open-Meteo port weather: per-port cache, forecast only from today, 'may' wording."""
import json
import os
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from corkathon import server
from corkathon.sources import open_meteo as om
from corkathon.sources.base import SourceResult

FIX = json.loads((Path(__file__).parent / "fixtures" / "open_meteo_cork.json").read_text())
TODAY = date(2026, 11, 7)


def loader():
    return om.PortWeatherLoader("Cork", 51.84, -8.30)


class ParseTests(unittest.TestCase):
    def test_parse_merges_wind_and_waves(self):
        recs, ref, pub = loader().parse(FIX)
        self.assertEqual(len(recs), 7)
        self.assertEqual(ref, "2026-11-07")
        self.assertIsNone(pub)  # Open-Meteo gives no model run time; we don't invent one
        self.assertEqual(recs[3]["gust_max_kmh"], 96.1)
        self.assertEqual(recs[3]["wave_max_m"], 4.6)
        self.assertIsNone(recs[6]["wave_max_m"])

    def test_waves_are_optional(self):
        recs, _, _ = loader().parse({"wind": FIX["wind"], "wave": None})
        self.assertTrue(all(r["wave_max_m"] is None for r in recs))

    def test_no_daily_block_is_a_fetch_error(self):
        with self.assertRaises(om.FetchError):
            loader().parse({"wind": {}, "wave": None})

    def test_cache_key_and_urls_hold_one_public_port_only(self):
        lo = loader()
        self.assertEqual(lo.cache_key(), "weather-cork")
        for u in lo.urls():
            self.assertIn("latitude=51.84", u)
            self.assertNotIn("Santos", u)


class WordingTests(unittest.TestCase):
    def setUp(self):
        self.recs, _, _ = loader().parse(FIX)

    def test_rough_days_use_the_thresholds(self):
        self.assertEqual([r["date"] for r in om.rough_days(self.recs, TODAY)], ["2026-11-09", "2026-11-10"])

    def test_past_days_never_count(self):
        self.assertEqual(om.rough_days(self.recs, date(2026, 11, 11)), [])

    def test_sentence_says_may_and_names_the_worst_day(self):
        s = om.port_sentence("Cork", om.rough_days(self.recs, TODAY))
        self.assertIn("Cork on Mon 9 Nov, Tue 10 Nov", s)
        self.assertIn("gusts up to 96 km/h and waves up to 4.6 m", s)
        self.assertIn("may be delayed", s)
        self.assertNotIn("No action needed", s)


class SnapshotTests(unittest.TestCase):
    def test_snapshot_keeps_only_this_port(self):
        recs, _, _ = loader().parse(FIX)
        other = [dict(r, port="Dublin") for r in recs]
        snap = SourceResult("open_meteo", "e", om.PortWeatherLoader.licence, "snapshot", "2026-11-07T10:00:00+00:00",
                            mode="fallback", records=recs + other)
        with mock.patch("corkathon.sources.base.Loader.load_snapshot", return_value=snap):
            self.assertEqual({r["port"] for r in loader().load_snapshot().records}, {"Cork"})
        empty = SourceResult("open_meteo", "e", om.PortWeatherLoader.licence, "snapshot", "2026-11-07T10:00:00+00:00",
                             mode="fallback", records=other)
        with mock.patch("corkathon.sources.base.Loader.load_snapshot", return_value=empty):
            self.assertEqual(loader().load_snapshot().status, "unavailable")


class BlockTests(unittest.TestCase):
    def _fake_load(self, by_port):
        def load(self_):
            recs = by_port.get(self_.port)
            if recs is None:
                return SourceResult("open_meteo", "e", om.PortWeatherLoader.licence, "unavailable",
                                    "2026-11-07T10:00:00+00:00", mode="fallback")
            return SourceResult("open_meteo", "e", om.PortWeatherLoader.licence, "ok",
                                "2026-11-07T10:00:00+00:00", records=[dict(r, port=self_.port) for r in recs])
        return load

    def test_rough_calm_and_missing_ports_are_all_named(self):
        recs, _, _ = loader().parse(FIX)
        calm = [dict(r, gust_max_kmh=30.0, wave_max_m=1.0) for r in recs]
        with mock.patch.object(om.PortWeatherLoader, "load", self._fake_load({"Cork": recs, "Santos": calm})):
            w = server.weather_block(["Santos", "Rotterdam", "Cork"], today=TODAY)
        self.assertEqual(w["rough_ports"], ["Cork"])
        text = " ".join(w["lines"])
        self.assertIn("Rough weather forecast at Cork", text)
        self.assertIn("forecast at Santos in the next 7 days", text)
        self.assertIn("no weather forecast for Rotterdam", text)  # missing is never called calm
        self.assertEqual(w["reference_period"], "Next 7 days from 2026-11-07")

    def test_flag_off_means_no_weather(self):
        form = {"importer": "X", "origin_port": "Santos", "destination_port": "Cork", "currency": "EUR",
                "fixed_rate_share": "none", "stock_days": "21", "lead_time_days": "35",
                "window_start": "2026-11-07", "window_end": "2026-11-28"}
        with mock.patch.dict(os.environ, {"SNAPSHOT_ONLY": "1", "WEATHER_ENABLED": "0"}):
            self.assertNotIn("weather", server.answer(form))
        with mock.patch.dict(os.environ, {"SNAPSHOT_ONLY": "1", "WEATHER_ENABLED": "1"}):
            out = server.answer(form)
        self.assertIn("weather", out)  # no snapshot yet: says so, doesn't crash


if __name__ == "__main__":
    unittest.main()
