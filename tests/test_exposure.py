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


if __name__ == "__main__":
    unittest.main()
