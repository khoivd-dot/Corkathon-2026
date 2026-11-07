"""Wording and contract checks for the answer card examples (web/)."""
import json
import pathlib
import unittest

WEB = pathlib.Path(__file__).resolve().parent.parent / "web"
REQUIRED_SOURCE_DATES = ("reference_period", "published_at", "retrieved_at")


class AnswerExamples(unittest.TestCase):
    def load(self, name):
        return json.loads((WEB / "examples" / f"{name}.json").read_text(encoding="utf-8"))

    def test_every_source_has_three_dates_and_a_use(self):
        for name in ("alert", "insufficient"):
            for s in self.load(name)["sources"]:
                for k in REQUIRED_SOURCE_DATES + ("use", "name"):
                    self.assertIn(k, s, f"{name}: {s.get('name')} missing {k}")

    def test_insufficient_never_claims_safety(self):
        a = self.load("insufficient")
        text = json.dumps(a).lower()
        self.assertNotIn("no action needed", text)
        self.assertIn("can't determine", a["headline"].lower())

    def test_ais_is_not_used(self):
        for name in ("alert", "insufficient"):
            ais = [s for s in self.load(name)["sources"] if "AIS" in s["name"]]
            for s in ais:
                self.assertTrue(s["use"].startswith("Not used"))

    def test_headlines_avoid_bare_minus(self):
        for name in ("alert", "insufficient"):
            self.assertNotIn("\u2212", self.load(name)["headline"])
            self.assertNotIn(" -", self.load(name)["headline"])

    def test_renderer_uses_text_content_only(self):
        js = (WEB / "app.js").read_text(encoding="utf-8")
        self.assertNotIn("innerHTML", js)

    def test_no_third_party_hosts(self):
        html = (WEB / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("http://", html)
        self.assertNotIn("https://", html)


if __name__ == "__main__":
    unittest.main()
