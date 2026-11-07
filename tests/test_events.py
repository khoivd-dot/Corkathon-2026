import unittest
from datetime import date

from corkathon.events import Lane, filter_events, lane_query


def inc(title, day, urls=("https://news.example.com/a",), n=1, domains=("news.example.com",)):
    return {"kind": "incident", "title": title, "first_seen": f"{day}T08:00:00Z",
            "last_seen": f"{day}T09:00:00Z", "urls": list(urls), "article_count": n,
            "domains": list(domains)}


LANE = Lane(origin_port="Santos", destination_port="Cork", transshipment_ports=("Rotterdam",))
W = (date(2026, 10, 25), date(2026, 11, 7))


class EventTests(unittest.TestCase):
    def test_off_lane_dropped(self):
        ev = filter_events([inc("Port strike in Durban halts cargo", "2026-11-05")], LANE, *W)
        self.assertEqual(ev, [])

    def test_on_lane_reported(self):
        ev = filter_events([inc("Rotterdam port strike halts container cargo", "2026-11-05", n=3)], LANE, *W)
        self.assertEqual(len(ev), 1)
        self.assertEqual(ev[0].status, "reported")
        self.assertEqual(ev[0].matched_places, ["Rotterdam"])
        self.assertEqual(ev[0].report_count, 3)

    def test_out_of_window_dropped(self):
        ev = filter_events([inc("Rotterdam port strike", "2026-09-01")], LANE, *W)
        self.assertEqual(ev, [])

    def test_duplicates_merged(self):
        recs = [inc("Rotterdam port strike halts container cargo", "2026-11-05"),
                inc("Rotterdam port strike halts cargo containers", "2026-11-06",
                    urls=("https://other.example.org/b",), domains=("other.example.org",))]
        ev = filter_events(recs, LANE, *W)
        self.assertEqual(len(ev), 1)
        self.assertEqual(ev[0].report_count, 2)

    def test_confirmed_only_from_carrier_or_port(self):
        recs = [inc("Rotterdam terminal closure notice", "2026-11-05",
                    urls=("https://www.portofrotterdam.com/en/news/closure",))]
        self.assertEqual(filter_events(recs, LANE, *W)[0].status, "reported")  # flag off by default
        ev = filter_events(recs, LANE, *W, confirm=True)[0]
        self.assertEqual(ev.status, "confirmed")
        self.assertTrue(ev.confirmation_url.startswith("https://www.portofrotterdam.com/"))
        spoof = [inc("Rotterdam terminal closure notice", "2026-11-05",
                     urls=("https://portofrotterdam.com.evil.example/x",))]
        self.assertEqual(filter_events(spoof, LANE, *W)[0].status, "reported")

    def test_no_lane_no_events(self):
        ev = filter_events([inc("Rotterdam port strike", "2026-11-05")], Lane("", ""), *W)
        self.assertEqual(ev, [])

    def test_word_boundary(self):
        lane = Lane(origin_port="Cork", destination_port="Cork")
        self.assertEqual(filter_events([inc("Corkscrew sales disrupted", "2026-11-05")], lane, *W), [])

    def test_lane_query_names_ports(self):
        q = lane_query(LANE)
        for p in ("Santos", "Rotterdam", "Cork", "port strike"):
            self.assertIn(p, q)

    def test_news_merged_with_port_page_stays_reported(self):
        recs = [inc("Rotterdam port strike halts container cargo", "2026-11-05",
                    urls=("https://news.example.com/a", "https://www.portofrotterdam.com/en/news"))]
        ev = filter_events(recs, LANE, *W)
        self.assertEqual(ev[0].status, "reported")
        self.assertIsNone(ev[0].confirmation_url)

    def test_port_page_off_lane_not_confirmed(self):
        recs = [inc("Durban terminal closure notice", "2026-11-05",
                    urls=("https://www.portofrotterdam.com/en/news/x",))]
        self.assertEqual(filter_events(recs, LANE, *W), [])

    def test_matching_domain_alone_is_reported(self):
        recs = [inc("Rotterdam welcomes new container terminal", "2026-11-05",
                    urls=("https://www.portofrotterdam.com/en/news/terminal",))]
        ev = filter_events(recs, LANE, *W, confirm=True)
        # Not a disruption, so it isn't an event at all, and never a confirmation.
        self.assertFalse([e for e in ev if e.status == "confirmed"])
        self.assertEqual(ev, [])

    def test_headline_needs_a_disruption_word(self):
        recs = [inc("Rotterdam hosts shipping conference", "2026-11-05"),
                inc("Strike halts cranes at Rotterdam", "2026-11-05")]
        ev = filter_events(recs, LANE, *W)
        self.assertEqual([e.title for e in ev], ["Strike halts cranes at Rotterdam"])
        self.assertIn("strike", ev[0].match_reason)

    def test_off_topic_port_name_is_dropped(self):
        recs = [inc("Santos FC delay stadium move", "2026-11-05"),
                inc("Cork hurling final delayed by storm", "2026-11-05")]
        lane = Lane("Santos", "Cork")
        self.assertEqual(filter_events(recs, lane, *W), [])


if __name__ == "__main__":
    unittest.main()
