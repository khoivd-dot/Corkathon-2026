import io
import logging
import os
import tempfile
import unittest
from pathlib import Path

from corkathon.inputs import InputError, QUESTIONS, parse_inputs

GOOD = {"importer": "Secret Coffee Ltd", "origin_port": "Santos", "destination_port": "Cork",
        "transshipment_ports": "Rotterdam, ", "currency": "usd", "fixed_rate_share": "Some", "fixed_rate_pct": "50",
        "stock_days": "21", "lead_time_days": "35", "window_start": "2026-11-10", "window_end": "2026-12-15"}


class InputTests(unittest.TestCase):
    def test_valid(self):
        i = parse_inputs(GOOD)
        self.assertEqual((i.currency, i.fixed_rate_share, i.transshipment_ports), ("USD", 0.5, ("Rotterdam",)))

    def test_all_errors_at_once(self):
        with self.assertRaises(InputError) as cm:
            parse_inputs({**GOOD, "origin_port": "", "stock_days": "lots", "currency": "XXX",
                          "window_end": "2026-11-01"})
        self.assertEqual(set(cm.exception.errors), {"origin_port", "stock_days", "currency", "window_end"})

    def test_plain_wording(self):
        self.assertNotIn("hedg", " ".join(QUESTIONS.values()).lower())

    def test_repr_redacts(self):
        i = parse_inputs(GOOD)
        self.assertNotIn("Secret", repr(i) + str(i))

    def test_nothing_written_to_disk_or_logs(self):
        with tempfile.TemporaryDirectory() as d:
            cwd = os.getcwd(); os.chdir(d)
            buf = io.StringIO(); h = logging.StreamHandler(buf)
            root = logging.getLogger(); root.addHandler(h); root.setLevel(logging.DEBUG)
            try:
                i = parse_inputs(GOOD)
                logging.getLogger("corkathon").info("parsed %s", i)
                try:
                    parse_inputs({**GOOD, "stock_days": "x"})
                except InputError as e:
                    logging.getLogger("corkathon").info("error %s", e)
            finally:
                root.removeHandler(h); os.chdir(cwd)
            self.assertEqual(list(Path(d).rglob("*")), [])
            self.assertNotIn("Secret", buf.getvalue())
            self.assertNotIn("Santos", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
