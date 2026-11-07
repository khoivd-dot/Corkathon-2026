import unittest

from corkathon.sources.ecb_fx import EcbFxLoader

from .helpers import env, fixture, no_network


class EcbFxTests(unittest.TestCase):
    def test_parse_fixture(self):
        recs, ref, pub = EcbFxLoader().parse(fixture("ecb_exr_usd.json"))
        self.assertEqual(len(recs), 10)
        self.assertEqual(ref, recs[-1]["reference_period"])
        self.assertEqual(sorted(r["reference_period"] for r in recs), [r["reference_period"] for r in recs])
        self.assertTrue(all(0.5 < r["usd_per_eur"] < 2 for r in recs))
        self.assertEqual(set(recs[0]), {"reference_period", "usd_per_eur", "published_at", "retrieved_at"})

    def test_snapshot_offline(self):
        with env(SNAPSHOT="1"), no_network():
            r = EcbFxLoader().load()
        self.assertEqual(r.status, "snapshot")
        self.assertEqual(r.licence.attribution, "Source: ECB statistics.")

    def test_live_failure_never_raises(self):
        with no_network():
            self.assertEqual(EcbFxLoader().load_live().status, "unavailable")
