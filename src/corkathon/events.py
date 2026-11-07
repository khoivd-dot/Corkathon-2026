"""Route-matched event filtering (PR E).

Takes GDELT incident records (already deduplicated per query by the loader)
and the user's *confirmed* lane, and returns only events that name a port or
chokepoint on that lane inside the order window. Routes are never inferred:
if the user gave no ports, nothing matches.

Status rules:
- "reported": only news reports (GDELT). Never treated as confirmation.
- "confirmed": at least one source URL is on a carrier/port domain in
  CONFIRMING_DOMAINS. GDELT alone can never produce this.
An alert still needs the decision engine's stock-exposure check on top.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from urllib.parse import urlparse

from .sources.gdelt import _jaccard, _tokens

# Official carrier and port authority domains. A URL on one of these (or a
# subdomain) counts as confirmation. Keep this list explicit and reviewed.
CONFIRMING_DOMAINS = frozenset({
    "maersk.com", "msc.com", "cma-cgm.com", "hapag-lloyd.com", "one-line.com",
    "evergreen-line.com", "cosco.com", "yangming.com", "zim.com",
    "portofcork.ie", "dublinport.ie", "portofrotterdam.com", "portofantwerpbruges.com",
    "hamburg-port-authority.de", "mpa.gov.sg", "suezcanal.gov.eg",
})


@dataclass(frozen=True)
class Lane:
    """The route the user confirmed. Every field comes from the user."""
    origin_port: str
    destination_port: str
    transshipment_ports: tuple[str, ...] = ()
    chokepoints: tuple[str, ...] = ()  # e.g. "Red Sea", "Suez", only if the user confirms
    carrier: str | None = None

    def places(self) -> list[str]:
        return [p for p in (self.origin_port, *self.transshipment_ports, *self.chokepoints,
                            self.destination_port) if p and p.strip()]


@dataclass
class Event:
    title: str
    matched_places: list[str]
    first_seen: str
    last_seen: str
    report_count: int
    source_urls: list[str]
    status: str  # "reported" | "confirmed"
    match_reason: str
    domains: list[str] = field(default_factory=list)


def _dt(s: str) -> datetime:
    return datetime.strptime(s[:10], "%Y-%m-%d")


def _domain_confirms(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == d or host.endswith("." + d) for d in CONFIRMING_DOMAINS)


def _mentions(text: str, place: str) -> bool:
    return re.search(r"\b" + re.escape(place.lower()) + r"\b", text.lower()) is not None


def lane_query(lane: Lane) -> str:
    """A tighter GDELT query: disruption terms AND a place on the user's lane."""
    places = " OR ".join(f'"{p}"' for p in lane.places())
    terms = '("port strike" OR "port closure" OR "port congestion" OR "shipping disruption" OR "vessel diverted" OR "blank sailing")'
    return f"{terms} ({places})" if places else terms


def filter_events(records: list[dict], lane: Lane, window_start: date, window_end: date,
                  merge_threshold: float = 0.5) -> list[Event]:
    places = lane.places()
    if not places:
        return []
    lo, hi = datetime.combine(window_start, datetime.min.time()), datetime.combine(window_end, datetime.min.time())
    kept = []
    for r in records:
        if r.get("kind") != "incident" or not r.get("last_seen"):
            continue
        if _dt(r["last_seen"]) < lo or _dt(r["first_seen"]) > hi:
            continue
        hits = [p for p in places if _mentions(r.get("title", ""), p)]
        if hits:
            kept.append((r, hits))
    # Merge incidents from different queries that describe the same story.
    groups: list[list[tuple[dict, list[str]]]] = []
    for item in kept:
        t = _tokens(item[0].get("title", ""))
        for g in groups:
            g0 = g[0][0]
            close = abs((_dt(g0["last_seen"]) - _dt(item[0]["last_seen"])).days) <= 1
            if close and _jaccard(t, _tokens(g0.get("title", ""))) >= merge_threshold:
                g.append(item); break
        else:
            groups.append([item])
    events = []
    for g in groups:
        urls = list(dict.fromkeys(u for r, _ in g for u in r.get("urls", [])))
        matched = sorted({p for _, h in g for p in h})
        confirmed = any(_domain_confirms(u) for u in urls)
        events.append(Event(
            title=g[0][0].get("title", "").strip(), matched_places=matched,
            first_seen=min(r["first_seen"] for r, _ in g), last_seen=max(r["last_seen"] for r, _ in g),
            report_count=sum(r.get("article_count", 1) for r, _ in g), source_urls=urls[:5],
            status="confirmed" if confirmed else "reported",
            match_reason="names " + ", ".join(matched) + " on your confirmed route",
            domains=sorted({d for r, _ in g for d in r.get("domains", [])}),
        ))
    events.sort(key=lambda e: e.last_seen, reverse=True)
    return events


def default_window(today: date, lead_time_days: int) -> tuple[date, date]:
    """Look back 14 days for news; nothing beyond today exists yet."""
    return today - timedelta(days=14), today
