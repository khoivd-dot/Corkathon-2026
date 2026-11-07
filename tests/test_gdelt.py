import unittest
from unittest import mock

from corkathon.sources import gdelt
from corkathon.sources.gdelt import GdeltLoader, dedupe

from .helpers import env, fixture, no_network


def art(title, domain, day="20261107", url=None):
    return {"title": title, "domain": domain, "seendate": f"{day}T090000Z",
            "url": url or f"https://{domain}/{abs(hash(title))}"}


class DedupeTests(unittest.TestCase):
    def test_syndicated_copies_collapse(self):
        t = "Iran says wont allow US warships to get close as Trump ponders new attack"
        g = dedupe([art(t, "a.com"), art(t + " - B News", "b.com"), art(t, "c.com")])
        self.assertEqual(len(g), 1)

    def test_distinct_stories_stay_apart(self):
        g = dedupe([art("Dockers strike at Rotterdam port", "a.com"),
                    art("Red Sea attacks reroute container ships", "b.com")])
        self.assertEqual(len(g), 2)

    def test_same_title_far_apart_in_time_not_merged(self):
        t = "Port congestion builds at Felixstowe"
        self.assertEqual(len(dedupe([art(t, "a.com", "20261101"), art(t, "b.com", "20261107")])), 2)

    def test_same_url_always_merges(self):
        g = dedupe([art("x one", "a.com", "20261101", "https://a/1"), art("y two", "b.com", "20261107", "https://a/1")])
        self.assertEqual(len(g), 1)


class GdeltLoaderTests(unittest.TestCase):
    def payload(self):
        return {"shipping_disruption": {"query": "q", "payload": fixture("gdelt_artlist.json")}}

    def test_parse_fixture_counts(self):
        recs, ref, pub = GdeltLoader().parse(self.payload())
        summary = recs[0]
        self.assertEqual(summary["kind"], "query_summary")
        self.assertEqual(summary["article_count"], 9)
        self.assertLess(summary["incident_count"], summary["article_count"])
        incidents = [r for r in recs if r["kind"] == "incident"]
        self.assertEqual(len(incidents), summary["incident_count"])
        self.assertEqual(sum(i["article_count"] for i in incidents), 9)
        self.assertTrue(ref.startswith("2026-11-07"))
        self.assertIsNone(pub)

    def test_rate_limit_text_is_unavailable(self):
        with mock.patch.object(gdelt, "http_get", return_value=b"Please limit requests to one every 5 seconds"):
            r = GdeltLoader().load_live()
        self.assertEqual(r.status, "unavailable")
        self.assertIn("rate limit", r.reason)

    def test_empty_result_is_ok_zero(self):
        recs, ref, _ = GdeltLoader().parse({"q": {"query": "q", "payload": {}}})
        self.assertEqual(recs[0]["incident_count"], 0)
        self.assertIsNone(ref)

    def test_snapshot_offline(self):
        with env(SNAPSHOT="1"), no_network():
            self.assertEqual(GdeltLoader().load().status, "snapshot")
