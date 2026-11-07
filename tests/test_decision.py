import json
import os
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest import mock

from corkathon.decision import ABSTAIN, decide, dates_line
from corkathon.inputs import parse_inputs
from corkathon.sources.base import Licence, SourceResult
from corkathon.sources.gdelt import PortGdeltLoader

EX = Path(__file__).parent / "fixtures" / "ui_examples"
LIC = Licence("x", "https://example.org", "Source: test.")
NOW = datetime(2026, 11, 7, 11, 5, tzinfo=timezone.utc)
FORM = {"importer": "Example Coffee Ltd", "origin_port": "Santos", "destination_port": "Cork",
        "transshipment_ports": "Rotterdam", "currency": "USD", "fixed_rate_share": "none",
        "stock_days": "21", "lead_time_days": "35", "window_start": "2026-10-24",
        "window_end": "2026-11-07"}


def src(sid, ref, checked="2026-11-07T10:40:00+00:00", records=()):
    return SourceResult(sid, "https://example.org", LIC, "ok", checked, reference_period=ref,
                        records=list(records))


ECB = [{"reference_period": "2026-10-07", "usd_per_eur": 1.09},
       {"reference_period": "2026-11-06", "usd_per_eur": 1.069}]
SOURCES = {"gdelt": src("gdelt", "2026-11-07T10:00:00Z"), "ecb_fx": src("ecb_fx", "2026-11-06", records=ECB),
           "cso_trade": src("cso_trade", "2026-08")}
PORT_NOTICE = {"kind": "incident", "title": "Rotterdam terminal closure notice", "first_seen": "2026-11-05T08:00:00Z",
               "last_seen": "2026-11-05T09:00:00Z", "article_count": 1, "domains": ["portofrotterdam.com"],
               "urls": ["https://www.portofrotterdam.com/en/news/closure"]}
NEWS = {**PORT_NOTICE, "title": "Rotterdam port congestion worsens", "domains": ["news.example"],
        "urls": ["https://news.example/a"], "article_count": 4}


def keys(d, prefix=""):
    out = set()
    for k, v in d.items():
        out.add(prefix + k)
        if isinstance(v, dict):
            out |= keys(v, prefix + k + ".")
    return out


class DecisionTests(unittest.TestCase):
    def run_(self, recs, form=FORM, confirm="0"):
        with mock.patch.dict(os.environ, {"CONFIRMATION_ENABLED": confirm}):
            return decide(parse_inputs(form), SOURCES, recs, now=NOW)

    def test_matches_ui_example_shape(self):
        out = self.run_([NEWS])
        for name in ("alert", "insufficient"):
            ex = json.loads((EX / f"{name}.json").read_text())
            want = {k for k in keys(ex) if not k.startswith("fx.") or k in ("fx.finding", "fx.source", "fx.as_of", "fx.reading", "fx.action")}
            self.assertFalse(want - keys(out), name)
            for row in out["sources"]:
                self.assertFalse(set(ex["sources"][0]) - set(row))
                for k in ("mode", "source_updated_at", "checked_at"):
                    self.assertIn(k, row)

    def test_flag_off_never_confirms_or_alerts(self):
        out = self.run_([PORT_NOTICE, NEWS])
        self.assertEqual(out["state"], "insufficient")
        self.assertEqual(out["headline"], ABSTAIN)
        self.assertTrue(all(f["status"] == "reported" for f in out["delay"]["findings"]))
        self.assertIn("runs out 14 days before", out["delay"]["action"])  # shortfall still shown

    def test_alert_needs_confirmed_and_shortfall(self):
        out = self.run_([PORT_NOTICE], confirm="1")
        self.assertEqual(out["state"], "alert")
        covered = self.run_([PORT_NOTICE], form={**FORM, "stock_days": "40"}, confirm="1")
        self.assertEqual(covered["state"], "covered")
        self.assertEqual(covered["headline"],
                         "A confirmed event may affect your route. Your stock covers your lead time by 5 days.")

    def test_news_is_worded_reported(self):
        f = self.run_([NEWS])["delay"]["findings"][0]
        self.assertIn("reports (not confirmed)", f["text"])

    def test_never_no_action_needed(self):
        for recs in ([], [NEWS], [PORT_NOTICE]):
            for stock in ("10", "60"):
                for c in ("0", "1"):
                    blob = json.dumps(self.run_(recs, form={**FORM, "stock_days": stock}, confirm=c))
                    self.assertNotIn("no action needed", blob.lower())

    def test_uncovered_ports_line_with_links(self):
        cov = self.run_([])["coverage"]
        self.assertEqual(cov["line"], "We can't confirm events at Rotterdam, Antwerp, Felixstowe, Dublin or Cork "
                                      "automatically. Check their notices directly.")
        self.assertEqual(len(cov["ports"]), 5)
        self.assertTrue(all(p["url"].startswith("https://") for p in cov["ports"]))
        out = self.run_([])
        self.assertEqual(out["coverage_gaps"], cov["ports"])
        self.assertIn("Check their notices directly", out["coverage_line"])
        self.assertNotIn("\u2212", out["delay"]["exposure"]["arithmetic"])
        self.assertNotIn("= -", out["delay"]["exposure"]["arithmetic"])
        self.assertIn("You're 14 days short.", out["delay"]["exposure"]["arithmetic"])

    def test_no_last_order_claim_in_examples(self):
        for f in Path("web/examples").glob("*.json"):
            self.assertNotIn("last order", f.read_text())

    def test_dates_line(self):
        self.assertEqual(dates_line("2026-11-07T11:05:00+00:00", SOURCES),
                         "Checked 11:05 UK time. Trade figures are August data, ECB rate as of 6 Nov, port news from 10:40.")

    def test_skipped_share_has_no_amount(self):
        out = self.run_([], form={**FORM, "fixed_rate_share": "some"})
        self.assertEqual(out["fx"]["status"], "needs_share")
        self.assertNotIn("eur_cost_change_pct", out["fx"])

    def test_port_cache_key_has_only_the_port(self):
        k = PortGdeltLoader("Cork (Ringaskiddy)").cache_key()
        self.assertEqual(k, "gdelt-port-cork-ringaskiddy")
        out = json.dumps(self.run_([NEWS]))
        self.assertNotIn("Example Coffee", k)
        self.assertIn("Example Coffee", out)  # echoed back in-memory only, never cached


if __name__ == "__main__":
    unittest.main()
