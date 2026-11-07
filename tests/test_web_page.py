"""Static checks on web/index.html: every local asset exists, and the merged page keeps both
the redesign (#42) and the timing layer (#46) in the agreed order."""
import re
import unittest
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "web"
HTML = (WEB / "index.html").read_text(encoding="utf-8")


class TestWebPage(unittest.TestCase):
    def test_local_assets_exist(self):
        refs = re.findall(r'(?:src|href|srcset)="([^"#:]+)"', HTML)
        self.assertTrue(refs)
        for ref in refs:
            with self.subTest(ref=ref):
                self.assertTrue((WEB / ref.split(" ")[0]).is_file(), f"index.html points at missing {ref}")

    def test_no_merge_markers(self):
        for name in ("index.html", "app.js", "styles.css", "timing.js", "timing.css"):
            text = (WEB / name).read_text(encoding="utf-8")
            with self.subTest(file=name):
                self.assertNotRegex(text, r"(?m)^(<{7}|={7}|>{7})( |$)")

    def test_redesign_hero_and_timing_mounts(self):
        self.assertIn('class="hero-stack', HTML)  # #42 card-stack hero, not a screenshot
        for mount in ("mount-understood", "mount-order-by", "mount-timeline", "mount-asof"):
            self.assertEqual(HTML.count(f'id="{mount}"'), 1, mount)
        # The answer leads with the headline and today's step; "When to order" follows.
        self.assertLess(HTML.index('id="answer"'), HTML.index('id="todo"'))
        self.assertLess(HTML.index('id="todo"'), HTML.index('id="mount-order-by"'))
        self.assertLess(HTML.index('timing.js'), HTML.index('app.js'))


if __name__ == "__main__":
    unittest.main()
