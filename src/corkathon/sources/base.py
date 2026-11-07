"""Shared loader base (PR A): result shape, live-first fetch, cache, fallback.

Result fields: source_id, endpoint, licence, reference_period, published_at,
source_updated_at (when the data itself last changed), checked_at (when we
fetched it), retrieved_at (deprecated alias of checked_at), status
(ok | stale | unavailable | snapshot), mode (live | fallback), reason, records.

Order in load():
1. SNAPSHOT_ONLY=1 (or legacy SNAPSHOT=1): tests/CI only, no network.
2. Fresh cache entry in CACHE_DIR (default ./.cache) within the loader's TTL.
3. Live fetch; on success write the cache.
4. On live failure: stale cache entry if any (status="stale"), else the newest
   dated snapshot, both with mode="fallback". Neither -> "unavailable".

The cache holds source results only. Nothing a user typed ever goes here.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATUSES = ("ok", "stale", "unavailable", "snapshot")
MODES = ("live", "fallback")
DAY, MONTH = 86400, 31 * 86400
REPO_ROOT = Path(__file__).resolve().parents[3]
SNAPSHOT_DIR = Path(os.environ.get("SNAPSHOT_DIR", REPO_ROOT / "data" / "snapshots"))
USER_AGENT = "corkathon-2026/0.1 (+https://github.com/khoivd-dot/Corkathon-2026)"
TIMEOUT_S = float(os.environ.get("SOURCE_TIMEOUT_S", "20"))


def cache_dir() -> Path:
    return Path(os.environ.get("CACHE_DIR", ".cache"))


@dataclass
class Licence:
    name: str
    url: str
    attribution: str


@dataclass
class SourceResult:
    source_id: str
    endpoint: str
    licence: Licence
    status: str
    checked_at: str
    mode: str = "live"
    reference_period: str | None = None  # the period the data covers
    published_at: str | None = None  # when the publisher released it
    source_updated_at: str | None = None  # when the data itself last changed
    reason: str | None = None
    records: list[dict[str, Any]] = field(default_factory=list)
    retrieved_at: str | None = None  # deprecated alias of checked_at

    def __post_init__(self) -> None:
        if self.status not in STATUSES:
            raise ValueError(f"bad status {self.status!r}")
        if self.mode not in MODES:
            raise ValueError(f"bad mode {self.mode!r}")
        self.retrieved_at = self.checked_at
        if self.source_updated_at is None:
            self.source_updated_at = self.published_at or self.reference_period

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "SourceResult":
        d = dict(d)
        d["licence"] = Licence(**d["licence"])
        d.setdefault("checked_at", d.get("retrieved_at"))
        known = cls.__dataclass_fields__
        return cls(**{k: v for k, v in d.items() if k in known})


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class FetchError(Exception):
    """Raised inside fetch/parse; always caught by Loader.load()."""


def http_get(url: str, data: bytes | None = None, timeout: float = TIMEOUT_S) -> bytes:
    req = urllib.request.Request(url, data=data, headers={"User-Agent": USER_AGENT})
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise FetchError(f"network: {e}") from e


def http_json(url: str, data: bytes | None = None) -> Any:
    raw = http_get(url, data)
    try:
        return json.loads(raw)
    except ValueError as e:
        raise FetchError(f"not JSON: {raw[:120]!r}") from e


class Loader:
    source_id: str = ""
    endpoint: str = ""
    licence: Licence
    cache_ttl_s: int = DAY

    def fetch(self) -> Any:
        """Return raw payload from the network. May raise anything."""
        raise NotImplementedError

    def parse(self, payload: Any) -> tuple[list[dict], str | None, str | None]:
        """Return (records, reference_period, published_at). May raise."""
        raise NotImplementedError

    def _result(self, status: str, **kw: Any) -> SourceResult:
        return SourceResult(source_id=self.source_id, endpoint=self.endpoint,
                            licence=self.licence, status=status,
                            checked_at=kw.pop("checked_at", now_iso()), **kw)

    def load_live(self) -> SourceResult:
        try:
            records, ref, pub = self.parse(self.fetch())
        except Exception as e:  # noqa: BLE001 - loaders never raise
            return self._result("unavailable", reason=f"{type(e).__name__}: {e}"[:300])
        return self._result("ok", records=records, reference_period=ref, published_at=pub)

    def load_snapshot(self, reason: str | None = None) -> SourceResult:
        path = latest_snapshot(self.source_id, os.environ.get("SNAPSHOT_DATE"))
        if path is None:
            return self._result("unavailable", mode="fallback", reason=(reason or "") + " | no snapshot")
        res = SourceResult.from_dict(json.loads(path.read_text()))
        res.status, res.mode = "snapshot", "fallback"
        res.reason = f"snapshot {path.stem}" + (f" (live failed: {reason})" if reason else "")
        return res

    # --- cache -----------------------------------------------------------
    def cache_key(self) -> str:
        return self.source_id

    def _cache_path(self) -> Path:
        return cache_dir() / f"{self.cache_key()}.json"

    def read_cache(self) -> tuple[SourceResult, float] | None:
        p = self._cache_path()
        try:
            res = SourceResult.from_dict(json.loads(p.read_text()))
        except (OSError, ValueError, TypeError, KeyError):
            return None
        checked = datetime.fromisoformat(res.checked_at.replace("Z", "+00:00"))
        return res, (datetime.now(timezone.utc) - checked).total_seconds()

    def write_cache(self, res: SourceResult) -> None:
        p = self._cache_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(res.to_dict(), ensure_ascii=False))
        tmp.replace(p)

    def load(self) -> SourceResult:
        if os.environ.get("SNAPSHOT_ONLY") == "1" or os.environ.get("SNAPSHOT") == "1":
            return self.load_snapshot()
        cached = self.read_cache()
        if cached and cached[1] < self.cache_ttl_s and cached[0].status == "ok":
            return cached[0]
        res = self.load_live()
        if res.status == "ok":
            self.write_cache(res)
            return res
        if cached:
            stale = cached[0]
            stale.status, stale.mode = "stale", "fallback"
            stale.reason = f"cached {stale.checked_at} (live failed: {res.reason})"
            return stale
        return self.load_snapshot(res.reason)


def latest_snapshot(source_id: str, date: str | None = None) -> Path | None:
    d = SNAPSHOT_DIR / source_id
    if date:
        p = d / f"{date}.json"
        return p if p.exists() else None
    files = sorted(d.glob("*.json")) if d.exists() else []
    return files[-1] if files else None


def write_snapshot(res: SourceResult) -> Path:
    day = res.checked_at[:10]
    p = SNAPSHOT_DIR / res.source_id / f"{day}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(res.to_dict(), indent=1, ensure_ascii=False) + "\n")
    return p
