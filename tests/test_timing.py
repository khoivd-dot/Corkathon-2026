"""Tests for timing calculation engine."""
import unittest
from datetime import date

from corkathon.timing import compute_delays_for_date, compute_timing, effective_lead

SAMPLE_HOLIDAYS = [
    {"country": "CN", "date": "2027-02-06", "name": "Chinese New Year (Spring Festival)", "global": True},
    {"country": "IE", "date": "2026-12-25", "name": "Christmas Day", "global": True},  # Friday
    {"country": "IE", "date": "2026-12-26", "name": "St Stephen's Day", "global": True},  # Saturday
]


class TestTimingEngine(unittest.TestCase):
    def test_shanghai_to_dublin_november(self):
        # Shanghai (CN) -> Dublin (IE), stock 70, lead 42, as_of 2026-11-07
        # -> order_by 2026-12-05, days_left 28, no delays
        res = compute_timing(
            stock_days=70,
            lead_days=42,
            origin_country="CN",
            dest_country="IE",
            holidays=SAMPLE_HOLIDAYS,
            notices=[],
            as_of="2026-11-07",
            origin_port="Shanghai",
            dest_port="Dublin",
        )
        self.assertEqual(res["order_by"], "2026-12-05")
        self.assertEqual(res["days_left"], 28)
        self.assertEqual(len(res["delays"]), 0)
        self.assertEqual(res["status"], "plan")
        self.assertEqual(res["headline"], "Order by Sat 5 Dec.")
        self.assertEqual(res["reason"], "No holidays on your route change this date.")

    def test_shanghai_to_dublin_december_cny_demo(self):
        # Same, as_of 2026-12-20 -> order_by 2027-01-03, days_left 14, one CNY rule delay
        # "January vs June" demo
        res = compute_timing(
            stock_days=70,
            lead_days=42,
            origin_country="CN",
            dest_country="IE",
            holidays=SAMPLE_HOLIDAYS,
            notices=[],
            as_of="2026-12-20",
            origin_port="Shanghai",
            dest_port="Dublin",
        )
        self.assertEqual(res["order_by"], "2027-01-03")
        self.assertEqual(res["days_left"], 14)
        self.assertEqual(len(res["delays"]), 1)
        cny = res["delays"][0]
        self.assertTrue(cny["rule"])
        self.assertEqual(cny["days_added"], 14)
        self.assertEqual(cny["place"], "Shanghai")
        self.assertEqual(res["status"], "plan")
        self.assertEqual(res["headline"], "Order by Sun 3 Jan.")
        self.assertEqual(
            res["reason"],
            "After that, Chinese New Year at Shanghai (6 Feb) pushes arrival past the day your stock runs out.",
        )
        self.assertEqual(len(res["assumptions"]), 1)
        self.assertIn("rule of thumb", res["assumptions"][0])

    def test_shanghai_to_dublin_june(self):
        # Same, as_of 2027-06-01 -> days_left 28
        res = compute_timing(
            stock_days=70,
            lead_days=42,
            origin_country="CN",
            dest_country="IE",
            holidays=SAMPLE_HOLIDAYS,
            notices=[],
            as_of="2027-06-01",
            origin_port="Shanghai",
            dest_port="Dublin",
        )
        self.assertEqual(res["days_left"], 28)
        self.assertEqual(res["order_by"], "2027-06-29")
        self.assertEqual(res["status"], "plan")

    def test_stock_shortfall_late_status(self):
        # Stock 21, lead 35 -> status "late"
        res = compute_timing(
            stock_days=21,
            lead_days=35,
            origin_country="CN",
            dest_country="IE",
            holidays=SAMPLE_HOLIDAYS,
            notices=[],
            as_of="2026-11-07",
            origin_port="Shanghai",
            dest_port="Dublin",
        )
        self.assertEqual(res["status"], "late")
        self.assertEqual(res["order_by"], "2026-11-07")
        self.assertEqual(res["days_left"], 0)
        self.assertIn("arrives 14 days after your stock runs out", res["reason"])

    def test_weekend_holiday_adds_nothing(self):
        # 2026-12-26 is Saturday
        weekend_holiday = [{"country": "IE", "date": "2026-12-26", "name": "Saturday Holiday", "global": True}]
        delays = compute_delays_for_date(
            d=date(2026, 12, 20),
            lead_days=7,
            origin_country="CN",
            dest_country="IE",
            holidays=weekend_holiday,
        )
        # Saturday holiday should NOT be added
        self.assertEqual(len(delays), 0)

    def test_weekday_holiday_adds_one_day(self):
        # 2026-12-25 is Friday (weekday)
        friday_holiday = [{"country": "IE", "date": "2026-12-25", "name": "Christmas Day", "global": True}]
        delays = compute_delays_for_date(
            d=date(2026, 12, 18),
            lead_days=7,  # base arrival 2026-12-25, arrival window [12-22, 12-25]
            origin_country="CN",
            dest_country="IE",
            holidays=friday_holiday,
        )
        self.assertEqual(len(delays), 1)
        self.assertEqual(delays[0]["days_added"], 1)


if __name__ == "__main__":
    unittest.main()
