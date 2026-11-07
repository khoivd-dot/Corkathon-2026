import unittest

from corkathon.sources.comext import ComextLoader

from .helpers import env, fixture, no_network


class ComextTests(unittest.TestCase):
    def test_parse_fixture(self):
        recs, ref, pub = ComextLoader().parse(fixture("comext_ie_0901.json"))
        self.assertGreaterEqual(len(recs), 12)
        self.assertEqual(ref, recs[-1]["reference_period"])
        r = recs[-1]
        self.assertIn("value_eur", r); self.assertIn("quantity_100kg", r)
        self.assertEqual(r["product_code"], "0901")
        self.assertTrue(pub and r["retrieved_at"])

    def test_empty_is_error_not_ok(self):
        ds = fixture("comext_ie_0901.json"); ds["value"] = {}
        with self.assertRaises(ValueError):
            ComextLoader().parse(ds)

    def test_snapshot_offline(self):
        with env(SNAPSHOT="1"), no_network():
            self.assertEqual(ComextLoader().load().status, "snapshot")
