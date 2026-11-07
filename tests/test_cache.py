import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from corkathon.sources import base
from corkathon.sources.base import FetchError, Licence, Loader


class Fake(Loader):
    source_id = "fake"
    endpoint = "https://example.invalid"
    licence = Licence("x", "https://example.invalid", "x")
    cache_ttl_s = 60

    def __init__(self, fail=False):
        self.fail, self.calls = fail, 0

    def fetch(self):
        self.calls += 1
        if self.fail:
            raise FetchError("down")
        return {"v": 1}

    def parse(self, payload):
        return [payload], "2026-08", "2026-10-16"


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.snap = Path(self.tmp.name) / "snap"
        env = {"CACHE_DIR": str(Path(self.tmp.name) / "cache")}
        self.env = mock.patch.dict(os.environ, env)
        self.env.start()
        for k in ("SNAPSHOT", "SNAPSHOT_ONLY", "SNAPSHOT_DATE"):
            os.environ.pop(k, None)
        self.snapdir = mock.patch.object(base, "SNAPSHOT_DIR", self.snap)
        self.snapdir.start()

    def tearDown(self):
        self.snapdir.stop(); self.env.stop(); self.tmp.cleanup()

    def test_live_then_cache_hit(self):
        f = Fake()
        r1 = f.load()
        self.assertEqual((r1.status, r1.mode), ("ok", "live"))
        self.assertEqual(r1.source_updated_at, "2026-10-16")
        self.assertEqual(r1.retrieved_at, r1.checked_at)
        r2 = f.load()
        self.assertEqual(f.calls, 1)
        self.assertEqual(r2.records, r1.records)

    def test_expired_entry_refetches(self):
        f = Fake(); f.load()
        p = Path(os.environ["CACHE_DIR"]) / "fake.json"
        d = json.loads(p.read_text())
        d["checked_at"] = (datetime.now(timezone.utc) - timedelta(seconds=120)).isoformat()
        p.write_text(json.dumps(d))
        f.load()
        self.assertEqual(f.calls, 2)

    def test_live_failure_serves_stale_cache(self):
        Fake().load()
        p = Path(os.environ["CACHE_DIR"]) / "fake.json"
        d = json.loads(p.read_text())
        d["checked_at"] = (datetime.now(timezone.utc) - timedelta(seconds=120)).isoformat()
        p.write_text(json.dumps(d))
        r = Fake(fail=True).load()
        self.assertEqual((r.status, r.mode), ("stale", "fallback"))

    def test_live_failure_falls_back_to_snapshot(self):
        r = Fake().load_live()
        (self.snap / "fake").mkdir(parents=True)
        (self.snap / "fake" / "2026-11-07.json").write_text(json.dumps(r.to_dict()))
        out = Fake(fail=True).load()
        self.assertEqual((out.status, out.mode), ("snapshot", "fallback"))
        self.assertIn("2026-11-07", out.reason)

    def test_nothing_available(self):
        out = Fake(fail=True).load()
        self.assertEqual((out.status, out.mode), ("unavailable", "fallback"))

    def test_snapshot_only_never_fetches(self):
        os.environ["SNAPSHOT_ONLY"] = "1"
        f = Fake(); f.load()
        self.assertEqual(f.calls, 0)

    def test_old_snapshot_shape_still_loads(self):
        d = {"source_id": "fake", "endpoint": "e", "licence": {"name": "x", "url": "u", "attribution": "a"},
             "status": "ok", "retrieved_at": "2026-11-07T10:00:00+00:00", "reference_period": "2026-08",
             "published_at": None, "reason": None, "records": []}
        r = base.SourceResult.from_dict(d)
        self.assertEqual(r.checked_at, "2026-11-07T10:00:00+00:00")
        self.assertEqual(r.source_updated_at, "2026-08")


if __name__ == "__main__":
    unittest.main()
