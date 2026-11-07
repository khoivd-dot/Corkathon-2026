"""Tests for Nager.Date public holidays loader."""
import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from corkathon.sources.holidays import (
    HolidaysLoader,
    country_for_port,
    load_holidays_for_country,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestHolidays(unittest.TestCase):
    def test_country_for_port(self):
        self.assertEqual(country_for_port("Cork"), "IE")
        self.assertEqual(country_for_port("Ringaskiddy"), "IE")
        self.assertEqual(country_for_port("Cork (Ringaskiddy)"), "IE")
        self.assertEqual(country_for_port("Dublin"), "IE")
        self.assertEqual(country_for_port("Shanghai"), "CN")
        self.assertEqual(country_for_port("Rotterdam"), "NL")
        self.assertEqual(country_for_port("Santos"), "BR")
        self.assertIsNone(country_for_port("UnknownPort123"))
        self.assertIsNone(country_for_port(""))

    def test_parse_filters_global_holidays(self):
        raw_cn = json.loads((FIXTURES_DIR / "holidays_cn_2027.json").read_text())
        loader = HolidaysLoader(country="CN", year=2027)
        records, ref, pub = loader.parse(raw_cn)
        self.assertEqual(ref, "2027")
        self.assertIsNone(pub)
        self.assertEqual(len(records), 6)
        # Check CNY record
        cny = next(r for r in records if "Chinese New Year" in r["name"])
        self.assertEqual(cny["date"], "2027-02-06")
        self.assertEqual(cny["country"], "CN")
        self.assertTrue(cny["global"])

    def test_load_snapshot_offline(self):
        with patch.dict(os.environ, {"SNAPSHOT_ONLY": "1"}):
            loader_ie = HolidaysLoader(country="IE", year=2026)
            res_ie = loader_ie.load()
            self.assertEqual(res_ie.status, "snapshot")
            self.assertEqual(res_ie.mode, "fallback")
            self.assertTrue(len(res_ie.records) > 0)
            self.assertTrue(all(r["country"] == "IE" and r["date"].startswith("2026-") for r in res_ie.records))

            loader_cn = HolidaysLoader(country="CN", year=2027)
            res_cn = loader_cn.load()
            self.assertEqual(res_cn.status, "snapshot")
            self.assertTrue(any(r["date"] == "2027-02-06" for r in res_cn.records))

    def test_load_holidays_for_country(self):
        with patch.dict(os.environ, {"SNAPSHOT_ONLY": "1"}):
            holidays = load_holidays_for_country("IE", years=(2026, 2027))
            self.assertTrue(len(holidays) >= 10)
            years = {h["date"][:4] for h in holidays}
            self.assertIn("2026", years)
            self.assertIn("2027", years)


if __name__ == "__main__":
    unittest.main()
