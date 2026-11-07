import unittest

from corkathon.exposure import fx_exposure, stock_exposure, stock_sentence


def ecb(*pairs):
    return [{"reference_period": d, "usd_per_eur": r} for d, r in pairs]


class StockTests(unittest.TestCase):
    def test_shortfall(self):
        s = stock_exposure(21, 35)
        self.assertEqual((s.buffer_days, s.shortfall), (-14, True))
        self.assertIn("21 \u2212 35 = -14", s.arithmetic)
        self.assertEqual(stock_sentence(s), "Your stock runs out 14 days before a new order would arrive.")

    def test_covers(self):
        self.assertEqual(stock_sentence(stock_exposure(50, 35)), "Your stock covers your lead time by 15 days.")


class FxTests(unittest.TestCase):
    def test_usd_weaker_euro_costs_more(self):
        f = fx_exposure("USD", 0.0, ecb(("2026-10-07", 1.20), ("2026-11-06", 1.10)))
        self.assertEqual(f.status, "computed")
        self.assertAlmostEqual(f.eur_cost_change_pct, 9.09, places=2)

    def test_fixed_share_scales(self):
        f = fx_exposure("USD", 0.5, ecb(("2026-10-07", 1.20), ("2026-11-06", 1.10)))
        self.assertAlmostEqual(f.eur_cost_change_pct, 4.55, places=2)

    def test_eur_and_fully_fixed_not_applicable(self):
        self.assertEqual(fx_exposure("EUR", 0, []).status, "not_applicable")
        self.assertEqual(fx_exposure("USD", 1.0, ecb(("2026-11-06", 1.1))).status, "not_applicable")

    def test_unknown_currency_unavailable(self):
        self.assertEqual(fx_exposure("CNY", 0, ecb(("2026-11-06", 1.1))).status, "unavailable")

    def test_fx_never_mentions_delay_confirmation(self):
        f = fx_exposure("USD", 0, ecb(("2026-11-06", 1.1)))
        self.assertIn("say nothing about delays", f.note)

    def test_some_without_share_shows_no_amount(self):
        from corkathon.inputs import parse_inputs
        from tests.test_inputs import GOOD
        i = parse_inputs({**GOOD, "fixed_rate_share": "Some", "fixed_rate_pct": ""})
        self.assertIsNone(i.fixed_rate_share)
        f = fx_exposure("USD", i.fixed_rate_share, ecb(("2026-10-07", 1.2), ("2026-11-06", 1.1)))
        self.assertEqual(f.status, "needs_share")
        self.assertIsNone(f.eur_cost_change_pct)
        self.assertEqual(f.note, "We need the share you've fixed to work out your euro cost.")

    def test_some_with_share(self):
        from corkathon.inputs import parse_inputs
        from tests.test_inputs import GOOD
        i = parse_inputs({**GOOD, "fixed_rate_share": "some", "fixed_rate_pct": "25%"})
        self.assertEqual(i.fixed_rate_share, 0.25)

    def test_fx_sentence_names_window(self):
        from corkathon.exposure import fx_sentence
        self.assertEqual(fx_sentence("2026-10-07", "2026-11-06", 4.55),
            "Since 7 Oct, the euro cost of the part you haven't fixed would be about 4.5% higher "
            "(ECB rate as of 6 Nov). This isn't your bank's rate. Ask for a current quote. Exchange rates say nothing about delays.")

    def test_no_half_default_anywhere(self):
        from corkathon.inputs import FIXED_SHARE
        self.assertNotIn(0.5, FIXED_SHARE.values())

    def test_gbp_and_cny_computed_from_snapshot(self):
        import json
        recs = next(v for v in json.load(open("data/snapshots/ecb_fx/2026-11-07.json")).values() if isinstance(v, list))
        for cur in ("GBP", "CNY", "JPY", "CHF", "USD"):
            self.assertEqual(fx_exposure(cur, 0.0, recs).status, "computed", cur)


if __name__ == "__main__":
    unittest.main()
