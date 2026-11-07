"""Tests for Met Éireann weather warnings loader."""
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from corkathon.sources.met_warnings import (
    MetWarningsLoader,
    is_expired,
    strip_html,
    warnings_for_port,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "met_warning_ireland.json"


class TestMetWarnings(unittest.TestCase):
    def setUp(self):
        self.raw_data = json.loads(FIXTURE_PATH.read_text())
        self.loader = MetWarningsLoader()

    def test_strip_html_preserves_wording(self):
        html_input = "<p>Areas of dense fog developing.</p><p>Potential impacts:</p><ul><li>Poor visibility</li><li>Difficult travelling conditions</li></ul>"
        clean = strip_html(html_input)
        self.assertEqual(
            clean,
            "Areas of dense fog developing. Potential impacts: Poor visibility Difficult travelling conditions",
        )
        # Empty string
        self.assertEqual(strip_html(""), "")
        # No tags
        self.assertEqual(strip_html("Plain text"), "Plain text")

    def test_verbatim_fields_untouched(self):
        ref_time = datetime(2026, 11, 7, 15, 0, 0, tzinfo=timezone.utc)
        records, ref, pub = self.loader.parse(self.raw_data, now=ref_time)
        self.assertEqual(len(records), 1)
        rec = records[0]
        raw_rec = self.raw_data[0]
        self.assertEqual(rec["headline"], raw_rec["headline"])
        self.assertEqual(rec["level"], raw_rec["level"].lower())
        self.assertEqual(rec["onset"], raw_rec["onset"])
        self.assertEqual(rec["expiry"], raw_rec["expiry"])
        self.assertEqual(rec["issued"], raw_rec["issued"])
        self.assertEqual(rec["type"], raw_rec["type"])
        self.assertEqual(rec["id"], raw_rec["capId"])
        self.assertEqual(rec["regions"], raw_rec["regions"])

    def test_expired_warning_dropped_in_parse(self):
        # Expiry is 2026-11-08T11:00:00+00:00
        # Check at 2026-11-08 12:00 UTC (after expiry)
        past_expiry = datetime(2026, 11, 8, 12, 0, 0, tzinfo=timezone.utc)
        records, ref, pub = self.loader.parse(self.raw_data, now=past_expiry)
        self.assertEqual(len(records), 0)

    def test_expired_warning_dropped_from_snapshot(self):
        with patch.dict("os.environ", {"SNAPSHOT_ONLY": "1"}):
            # When now is well past 2026-11-08
            with patch("corkathon.sources.met_warnings.datetime") as mock_dt:
                mock_dt.now.return_value = datetime(2026, 11, 9, 0, 0, 0, tzinfo=timezone.utc)
                mock_dt.fromisoformat = datetime.fromisoformat
                res = self.loader.load()
                self.assertEqual(res.status, "snapshot")
                self.assertEqual(len(res.records), 0)

    def test_warnings_for_port_matches_and_unknown_port_returns_empty(self):
        ref_time = datetime(2026, 11, 7, 22, 0, 0, tzinfo=timezone.utc)
        records, _, _ = self.loader.parse(self.raw_data, now=ref_time)

        # Cork (EI04)
        cork_warnings = warnings_for_port(records, "Cork", now=ref_time)
        self.assertEqual(len(cork_warnings), 1)
        self.assertEqual(cork_warnings[0]["headline"], records[0]["headline"])

        # Ringaskiddy (EI04)
        ringa_warnings = warnings_for_port(records, "Ringaskiddy", now=ref_time)
        self.assertEqual(len(ringa_warnings), 1)

        # Dublin (EI07)
        dublin_warnings = warnings_for_port(records, "Dublin", now=ref_time)
        self.assertEqual(len(dublin_warnings), 1)

        # Unknown or foreign port returns empty list
        self.assertEqual(warnings_for_port(records, "Rotterdam", now=ref_time), [])
        self.assertEqual(warnings_for_port(records, "Shanghai", now=ref_time), [])
        self.assertEqual(warnings_for_port(records, "UnknownPort", now=ref_time), [])
        self.assertEqual(warnings_for_port(records, "", now=ref_time), [])

    def test_warnings_for_port_drops_expired(self):
        records = [{
            "id": "exp-1",
            "headline": "Expired warning",
            "regions": ["EI04"],
            "expiry": "2026-11-08T11:00:00+00:00"
        }]
        now = datetime(2026, 11, 8, 12, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(warnings_for_port(records, "Cork", now=now), [])


if __name__ == "__main__":
    unittest.main()
