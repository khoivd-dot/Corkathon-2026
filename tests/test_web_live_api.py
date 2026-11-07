import pathlib, re, unittest
WEB = pathlib.Path(__file__).resolve().parents[1] / "web"

class LiveApiWiring(unittest.TestCase):
    def setUp(self):
        self.js = (WEB / "app.js").read_text(); self.html = (WEB / "index.html").read_text()
    def test_posts_to_answer_api(self):
        self.assertIn('fetch("/api/answer"', self.js); self.assertIn('method: "POST"', self.js)
    def test_no_client_storage_or_url_inputs(self):
        for bad in ("localStorage", "sessionStorage", "document.cookie", "history.pushState", "URLSearchParams"):
            self.assertNotIn(bad, self.js)
    def test_form_has_api_fields(self):
        for f in ("origin_port", "transshipment_ports", "destination_port", "currency", "fixed_rate_share", "fixed_rate_pct", "stock_days", "lead_time_days", "window_start", "window_end"):
            self.assertIn(f'name="{f}"', self.html)
    def test_banned_wording(self):
        for p in WEB.rglob("*"):
            if p.is_file(): self.assertNotIn("No action needed", p.read_text(errors="ignore"), p)
    def test_example_labels_undated(self):
        self.assertNotRegex(self.html, r"<option[^>]*>\s*\d{1,2} \w{3} 20\d\d")
