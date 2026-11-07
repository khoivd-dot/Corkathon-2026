"""The travel window is usually in the future; news is about the past.
A strike reported a few days ago must still reach a shipment sailing next week."""
import json
import os
import tempfile
import threading
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest import mock

from corkathon.decision import decide
from corkathon.events import Lane, filter_events, news_window
from corkathon.inputs import parse_inputs
from corkathon.sources.base import Licence, Loader, SourceResult

LANE = Lane(origin_port="Santos", destination_port="Cork", transshipment_ports=("Rotterdam",))
TODAY = date(2026, 11, 7)
FUTURE = (date(2026, 11, 7), date(2026, 11, 28))  # the page's default: today + 3 weeks


def inc(title, day, urls=("https://news.example.com/a",)):
    return {"kind": "incident", "title": title, "first_seen": f"{day}T08:00:00Z",
            "last_seen": f"{day}T09:00:00Z", "urls": list(urls), "article_count": 2,
            "domains": ["news.example.com"]}


class NewsWindowTests(unittest.TestCase):
    def test_window_reaches_back_two_weeks_from_today(self):
        self.assertEqual(news_window(*FUTURE, TODAY), (date(2026, 10, 24), date(2026, 11, 28)))

    def test_recent_strike_reaches_future_shipment(self):
        recs = [inc("Rotterdam port strike halts container cargo", "2026-11-04")]
        self.assertEqual(filter_events(recs, LANE, *FUTURE), [])  # the old behaviour
        lo, _ = news_window(*FUTURE, TODAY)
        ev = filter_events(recs, LANE, *FUTURE, news_from=lo)
        self.assertEqual([e.status for e in ev], ["reported"])

    def test_old_news_still_dropped(self):
        lo, _ = news_window(*FUTURE, TODAY)
        self.assertEqual(filter_events([inc("Rotterdam port strike", "2026-10-01")], LANE, *FUTURE, news_from=lo), [])

    def test_confirmation_still_needs_the_travel_window(self):
        recs = [inc("Rotterdam terminal closure notice", "2026-11-04",
                    urls=("https://www.portofrotterdam.com/en/news/closure",))]
        lo, _ = news_window(*FUTURE, TODAY)
        ev = filter_events(recs, LANE, *FUTURE, news_from=lo, confirm=True)
        self.assertEqual(ev[0].status, "reported")

    def test_decide_uses_the_lookback(self):
        form = {"importer": "X", "origin_port": "Santos", "transshipment_ports": "Rotterdam",
                "destination_port": "Cork", "currency": "EUR", "fixed_rate_share": "none",
                "stock_days": "21", "lead_time_days": "35",
                "window_start": "2026-11-07", "window_end": "2026-11-28"}
        lic = Licence("l", "u", "a")
        src = {"ecb_fx": SourceResult("ecb_fx", "e", lic, "ok", "2026-11-07T10:00:00+00:00", records=[])}
        out = decide(parse_inputs(form), src, [inc("Rotterdam port strike halts container cargo", "2026-11-04")],
                     now=datetime(2026, 11, 7, 12, tzinfo=timezone.utc))
        self.assertEqual(len(out["delay"]["findings"]), 1)


class _L(Loader):
    source_id = "racetest"
    licence = Licence("l", "u", "a")


class CacheWriteTests(unittest.TestCase):
    def test_concurrent_writes_never_raise(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ, {"CACHE_DIR": d}):
            res = SourceResult("racetest", "e", _L.licence, "ok", "2026-11-07T10:00:00+00:00")
            errors = []

            def go():
                try:
                    for _ in range(50):
                        _L().write_cache(res)
                except Exception as e:  # noqa: BLE001
                    errors.append(e)
            ts = [threading.Thread(target=go) for _ in range(6)]
            [t.start() for t in ts]; [t.join() for t in ts]
            self.assertEqual(errors, [])
            self.assertEqual(json.loads((Path(d) / "racetest.json").read_text())["source_id"], "racetest")
            self.assertEqual(list(Path(d).glob("*.tmp")), [])

    def test_unwritable_cache_is_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            blocker = Path(d) / "file"
            blocker.write_text("x")
            with mock.patch.dict(os.environ, {"CACHE_DIR": str(blocker / "sub")}):
                _L().write_cache(SourceResult("racetest", "e", _L.licence, "ok", "2026-11-07T10:00:00+00:00"))


if __name__ == "__main__":
    unittest.main()
