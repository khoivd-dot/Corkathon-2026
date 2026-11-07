"""The answer card's data label: live answers say 'Live public data'."""
import json, pathlib, re, shutil, subprocess, unittest

from corkathon.decision import _source_rows

WEB = pathlib.Path(__file__).resolve().parent.parent / "web"


def mode_label(ans):
    js = (WEB / "app.js").read_text(encoding="utf-8")
    fn = re.search(r"function modeLabel\(ans\) \{.*?\n  \}", js, re.S).group(0)
    out = subprocess.run(["node", "-e", fn + "\nprocess.stdout.write(modeLabel(" + json.dumps(ans) + "));"],
                         capture_output=True, text=True, check=True)
    return out.stdout


@unittest.skipUnless(shutil.which("node"), "node not installed")
class ModeLabel(unittest.TestCase):
    live = {"name": "ECB", "mode": "live", "status": "ok", "checked_at": "2026-11-07T11:00:00Z"}
    placeholder = {"name": "Carrier and port advisories", "mode": "not_used", "status": "unavailable", "checked_at": None}

    def test_live_answer_with_placeholder_is_live(self):
        self.assertEqual(mode_label({"sources": [self.live, self.placeholder]}), "Live public data")

    def test_real_fallback_still_says_saved_data(self):
        fb = dict(self.live, mode="fallback", status="stale")
        self.assertEqual(mode_label({"sources": [fb, self.placeholder]}),
                         "Live sources unavailable: using saved data")


class AdvisoriesRow(unittest.TestCase):
    def test_advisories_row_is_not_used_not_fallback(self):
        row = [r for r in _source_rows({}) if r["name"] == "Carrier and port advisories"][0]
        self.assertEqual(row["mode"], "not_used")
        self.assertNotEqual(row["mode"], "fallback")

    @unittest.skipUnless(shutil.which("node"), "node not installed")
    def test_rows_from_engine_label_live(self):
        self.assertEqual(mode_label({"sources": _source_rows({})}), "Live public data")
