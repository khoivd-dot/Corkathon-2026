"""Tests for plain-English shipment query parser."""
import unittest

from corkathon.inputs import parse_inputs
from corkathon.parse import parse_query


class TestParse(unittest.TestCase):
    def test_shanghai_homewares_query(self):
        q = "I bring homewares from Shanghai through Rotterdam to Dublin in dollars, about 10 weeks of stock, takes 6 weeks to get here"
        res = parse_query(q)
        self.assertEqual(res["missing"], [])
        self.assertEqual(res["fields"]["origin_port"], "Shanghai")
        self.assertEqual(res["fields"]["transshipment_ports"], "Rotterdam")
        self.assertEqual(res["fields"]["destination_port"], "Dublin")
        self.assertEqual(res["fields"]["currency"], "USD")
        self.assertEqual(res["fields"]["stock_days"], "70")
        self.assertEqual(res["fields"]["lead_time_days"], "42")
        # Ensure it passes inputs.parse_inputs without raising
        inputs = parse_inputs(res["fields"])
        self.assertEqual(inputs.origin_port, "Shanghai")
        self.assertEqual(inputs.destination_port, "Dublin")
        self.assertEqual(inputs.stock_days, 70)
        self.assertEqual(inputs.lead_time_days, 42)

    def test_santos_coffee_query(self):
        q = "Coffee from Santos via Rotterdam into Cork, paid in USD not fixed, 3 weeks left, 5 weeks to arrive"
        res = parse_query(q)
        self.assertEqual(res["missing"], [])
        self.assertEqual(res["fields"]["origin_port"], "Santos")
        self.assertEqual(res["fields"]["transshipment_ports"], "Rotterdam")
        self.assertEqual(res["fields"]["destination_port"], "Cork")
        self.assertEqual(res["fields"]["currency"], "USD")
        self.assertEqual(res["fields"]["fixed_rate_share"], "none")
        self.assertEqual(res["fields"]["stock_days"], "21")
        self.assertEqual(res["fields"]["lead_time_days"], "35")
        inputs = parse_inputs(res["fields"])
        self.assertEqual(inputs.origin_port, "Santos")
        self.assertEqual(inputs.destination_port, "Cork")

    def test_missing_stock_and_lead(self):
        q = "will my sterling order from Felixstowe to Dublin be late"
        res = parse_query(q)
        self.assertIn("stock_days", res["missing"])
        self.assertIn("lead_time_days", res["missing"])
        self.assertNotIn("origin_port", res["missing"])
        self.assertNotIn("destination_port", res["missing"])
        self.assertEqual(res["fields"]["origin_port"], "Felixstowe")
        self.assertEqual(res["fields"]["destination_port"], "Dublin")
        self.assertEqual(res["fields"]["currency"], "GBP")

    def test_garbage_and_long_input(self):
        garbage = "asdfghjkl random noise 12345 " * 10
        res = parse_query(garbage)
        self.assertEqual(res["fields"], {})
        self.assertEqual(res["understood"], [])
        self.assertTrue(len(res["missing"]) >= 4)

        long_garbage = "x" * 200
        res2 = parse_query(long_garbage)
        self.assertEqual(res2["fields"], {})
        self.assertTrue(len(res2["missing"]) >= 4)

    def test_fixed_share_variants(self):
        q_half = "homewares from Shanghai to Dublin in USD half fixed 4 weeks stock 6 weeks lead"
        res_half = parse_query(q_half)
        self.assertEqual(res_half["fields"]["fixed_rate_share"], "some")
        self.assertEqual(res_half["fields"]["fixed_rate_pct"], "50")

        q_full = "homewares from Shanghai to Dublin in USD fixed the rate 4 weeks stock 6 weeks lead"
        res_full = parse_query(q_full)
        self.assertEqual(res_full["fields"]["fixed_rate_share"], "all")


if __name__ == "__main__":
    unittest.main()
