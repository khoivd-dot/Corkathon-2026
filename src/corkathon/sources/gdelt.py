"""GDELT DOC 2.0 news signals: shipping / port disruption.

Fetches article lists per named query, collapses near-duplicate stories into
incidents (title similarity + date window, looser within one domain), and
exposes incident counts per query. News is a noisy *signal*, not proof.
Route matching and time-window filtering are deliberately out of scope here.
"""
from __future__ import annotations

import re
import threading
import time
from datetime import datetime
from typing import Any
from urllib.parse import urlencode

import json

from .base import FetchError, Licence, Loader, http_get, now_iso

API = "https://api.gdeltproject.org/api/v2/doc/doc"
DEFAULT_QUERIES = {
    "shipping_disruption": '("port strike" OR "shipping disruption" OR "Red Sea shipping" OR "port congestion")',
}
STOP = {"the", "a", "an", "of", "to", "in", "on", "for", "and", "as", "at", "is", "by", "with", "from", "s"}


def _tokens(title: str) -> set[str]:
    t = re.split(r"\s[\u2013\u2014|-]\s(?=[^\u2013\u2014|-]*$)", title)[0]  # drop " – Site name"
    return {w for w in re.findall(r"\w+", t.lower()) if w not in STOP}


def _jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def _day(seendate: str) -> datetime:
    return datetime.strptime(seendate[:8], "%Y%m%d")


def dedupe(articles: list[dict], cross_domain: float = 0.6, same_domain: float = 0.4,
           max_days: int = 1) -> list[list[dict]]:
    """Group articles into incidents with union-find. Exact URL repeats always merge."""
    n = len(articles)
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i

    toks = [_tokens(a.get("title", "")) for a in articles]
    for i in range(n):
        for j in range(i + 1, n):
            ai, aj = articles[i], articles[j]
            if ai.get("url") and ai.get("url") == aj.get("url"):
                parent[find(i)] = find(j); continue
            if abs((_day(ai["seendate"]) - _day(aj["seendate"])).days) > max_days:
                continue
            thr = same_domain if ai.get("domain") == aj.get("domain") else cross_domain
            if _jaccard(toks[i], toks[j]) >= thr:
                parent[find(i)] = find(j)
    groups: dict[int, list[dict]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(articles[i])
    return list(groups.values())


def _iso(seendate: str) -> str:
    return datetime.strptime(seendate, "%Y%m%dT%H%M%SZ").strftime("%Y-%m-%dT%H:%M:%SZ")


class RateGate:
    """Process-wide spacing for GDELT calls (GDELT asks for <= 1 request / 5 s).

    Every live GDELT request, from the background refresher or from a user's
    answer, reserves a slot here first. A caller that would have to wait longer
    than its budget gets False and falls back to the cache or the snapshot,
    so a burst of answers with unusual ports can't hammer GDELT or stall a page."""

    def __init__(self, interval_s: float = 5.5, clock=time.monotonic, sleep=time.sleep):
        self.interval_s, self._clock, self._sleep = interval_s, clock, sleep
        self._lock = threading.Lock()
        self._next = 0.0

    def acquire(self, wait_s: float) -> bool:
        with self._lock:
            now = self._clock()
            slot = max(now, self._next)
            if slot - now > wait_s:
                return False
            self._next = slot + self.interval_s
        if slot > now:
            self._sleep(slot - now)
        return True


GATE = RateGate()


class GdeltLoader(Loader):
    source_id = "gdelt"
    endpoint = API
    cache_ttl_s = 1800
    licence = Licence(
        name="GDELT dataset terms: reuse, snapshots and redistribution permitted with citation/link (checked 2026-11-07); publishers' full articles not licensed",
        url="https://www.gdeltproject.org/about.html#termsofuse",
        attribution="Source: The GDELT Project (gdeltproject.org).",
    )

    def __init__(self, queries: dict[str, str] | None = None, timespan: str = "14d",
                 max_records: int = 75, pause_s: float = 6.0, gate_wait_s: float = 60.0):
        self.queries = queries or DEFAULT_QUERIES
        self.timespan, self.max_records, self.pause_s = timespan, max_records, pause_s
        self.gate_wait_s = gate_wait_s

    def cache_key(self) -> str:
        import hashlib
        h = hashlib.sha256(json.dumps(self.queries, sort_keys=True).encode()).hexdigest()[:12]
        return f"{self.source_id}-{h}"

    def url(self, q: str) -> str:
        return f"{API}?" + urlencode({"query": q, "mode": "artlist", "format": "json",
                                      "maxrecords": self.max_records, "timespan": self.timespan,
                                      "sort": "datedesc"})

    def fetch(self) -> Any:
        out = {}
        for name, q in self.queries.items():
            if not GATE.acquire(self.gate_wait_s):
                raise FetchError("GDELT busy: waiting for a free slot (1 request / 5 s)")
            raw = http_get(self.url(q))
            if raw.lstrip().startswith(b"Please limit"):
                raise FetchError("GDELT rate limit (1 request / 5 s)")
            try:
                out[name] = {"query": q, "payload": json.loads(raw or b"{}")}
            except ValueError as e:
                raise FetchError(f"not JSON: {raw[:120]!r}") from e
        return out

    def parse(self, payload: Any):
        retrieved = now_iso()
        records: list[dict] = []
        latest = None
        for name, item in payload.items():
            arts = [a for a in item["payload"].get("articles", []) if a.get("seendate")]
            incidents = dedupe(arts)
            records.append({"kind": "query_summary", "query_id": name, "query": item["query"],
                            "timespan": self.timespan, "article_count": len(arts),
                            "incident_count": len(incidents), "retrieved_at": retrieved})
            for g in sorted(incidents, key=lambda g: max(a["seendate"] for a in g), reverse=True):
                g = sorted(g, key=lambda a: a["seendate"])
                last = _iso(g[-1]["seendate"])
                latest = max(latest or last, last)
                records.append({
                    "kind": "incident", "query_id": name, "title": g[0].get("title", "").strip(),
                    "article_count": len(g), "domains": sorted({a.get("domain", "") for a in g}),
                    "countries": sorted({a.get("sourcecountry", "") for a in g} - {""}),
                    "first_seen": _iso(g[0]["seendate"]), "last_seen": last,
                    "urls": [a["url"] for a in g][:5], "retrieved_at": retrieved,
                })
        # News has no publication batch; reference_period = newest article seen.
        return records, latest, None


def _slug(port: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", port.lower()).strip("-")


class PortGdeltLoader(GdeltLoader):
    """GDELT signals for a single public port. The cache key is the port name only,
    so no business's combined route, name, stock or invoice data reaches the cache."""

    def __init__(self, port: str, **kw):
        from ..events import confirmation_enabled, official_query, port_query
        self.port = port.strip()
        q = {_slug(self.port): port_query(self.port)}
        # With confirmation on, also ask GDELT for pages on official carrier and
        # port domains only. A headline from there that names a disruption and a
        # port on the route is what filter_events treats as confirmed.
        self.official = confirmation_enabled()
        if self.official:
            q[_slug(self.port) + "-official"] = official_query(self.port)
        super().__init__(queries=q, **kw)

    def cache_key(self) -> str:
        return f"gdelt-port-{_slug(self.port)}" + ("-official" if self.official else "")
