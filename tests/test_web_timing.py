"""Tests for timing UI examples and ICS contracts."""
import json
import unittest
from pathlib import Path

EXAMPLES_PATH = Path(__file__).resolve().parents[1] / "web" / "examples" / "timing.json"


class TestWebTiming(unittest.TestCase):
    def test_timing_examples_schema(self):
        self.assertTrue(EXAMPLES_PATH.exists(), f"missing {EXAMPLES_PATH}")
        data = json.loads(EXAMPLES_PATH.read_text(encoding="utf-8"))

        required_keys = ["cny_example", "late_example", "met_notice_example"]
        for k in required_keys:
            self.assertIn(k, data, f"missing example {k}")
            ex = data[k]
            # Required fields for icsFor
            self.assertIn("order_by", ex)
            self.assertIn("stock_out", ex)
            self.assertIn("headline", ex)
            self.assertIn("reason", ex)
            self.assertIn("assumptions", ex)
            self.assertIn("sources", ex)

            # Required fields for timeline and hero
            self.assertIn("as_of", ex)
            self.assertIn("days_left", ex)
            self.assertIn("status", ex)
            self.assertIn("delays", ex)
            self.assertIn("notices", ex)
            self.assertIn("base_lead_days", ex)

        # Check Met notice example has at least one notice with required fields
        met_ex = data["met_notice_example"]
        self.assertTrue(len(met_ex["notices"]) > 0)
        n0 = met_ex["notices"][0]
        self.assertIn("headline", n0)
        self.assertIn("onset", n0)
        self.assertIn("expiry", n0)
        self.assertIn("level", n0)


if __name__ == "__main__":
    unittest.main()
