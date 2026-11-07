"""F: the decision engine. Turns in-memory inputs plus loaded sources into the
answer-card JSON that the #8 UI reads (web/examples/*.json shape).

Rules (agreed in the Corkathon room):
- An alert needs a route-matched, deduplicated CONFIRMED event plus a stock shortfall.
- Confirmation is behind CONFIRMATION_ENABLED (off), so today every event is "reported".
- We never say "No action needed". When we can't tell, we abstain with ABSTAIN and
  still show any stock shortfall.
- Every source carries mode, source_updated_at and checked_at.
- Nothing here is written to disk or logged.
"""
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from .events import Event, confirmation_enabled, filter_events, news_window
from .exposure import FxExposure, fx_exposure, stock_exposure, stock_sentence
from .inputs import ImporterInputs, to_lane
from .ports import lookup
from .sources.base import SourceResult

ABSTAIN = "We can't determine whether your shipment is affected."
QUESTION = "Will my imports be late or dearer this month?"
UK = ZoneInfo("Europe/London")
# Ports we can't confirm automatically (no advisory feed cleared for reuse yet),
# with each port's own notices page. Researchy, 7 Nov 2026.
NOTICE_PAGES = {
    "Rotterdam": "https://pin.portofrotterdam.com/",
    "Antwerp": "https://www.portofantwerpbruges.com/en/shipping/nautical-messages",
    "Felixstowe": "https://hha.co.uk/category/notices-to-mariners/",
    "Dublin": "https://www.dublinport.ie/information-centre/notice-to-mariners-2026/",
    "Cork": "https://www.portofcork.ie/notices-to-mariners/",
}


def _join(xs: list[str]) -> str:
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " or " + xs[-1]


def coverage(confirm_on: bool) -> dict:
    """Behavioural Evidence: say which ports we can't check, so 'We can't determine'
    is never read as 'we checked everywhere'. With confirmation off, that's all five."""
    gaps = list(NOTICE_PAGES) if not confirm_on else []
    return {"line": f"We can't confirm events at {_join(gaps)} automatically. Check their notices directly."
            if gaps else "", "ports": [{"port": p, "url": NOTICE_PAGES[p]} for p in gaps]}
SOURCE_USE = {"gdelt": ("GDELT news", "Signal, duplicates merged"),
              "ecb_fx": ("ECB reference rates", "Cost answer only"),
              "cso_trade": ("CSO imports", "Context only"),
              "comext": ("Eurostat Comext", "Context only")}


def _when(iso: str | None) -> datetime | None:
    if not iso:
        return None
    try:
        d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        try:
            d = datetime.strptime(iso[:7], "%Y-%m")
        except ValueError:
            return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _day(iso: str | None) -> str:
    d = _when(iso)
    return f"{d.day} {d.strftime('%b %Y')}" if d else "\u2014"


def _month(iso: str | None) -> str:
    d = _when(iso)
    return d.strftime("%B") if d else "unknown"


def _hm(iso: str | None) -> str:
    d = _when(iso)
    return d.astimezone(UK).strftime("%H:%M") if d else "unknown"


def dates_line(checked_at: str, sources: dict[str, SourceResult]) -> str:
    """Behavioural Evidence's wording: 'Checked 11:05 UK time. Trade figures are
    August data, ECB rate as of 6 Nov, port news from 10:40.'"""
    parts = []
    trade = sources.get("cso_trade") or sources.get("comext")
    if trade:
        parts.append(f"Trade figures are {_month(trade.reference_period)} data")
    if "ecb_fx" in sources:
        d = _when(sources["ecb_fx"].reference_period)
        parts.append(f"ECB rate as of {d.day} {d.strftime('%b')}" if d else "ECB rate date unknown")
    if "gdelt" in sources:
        parts.append(f"port news from {_hm(sources['gdelt'].checked_at)}")
    tail = (" " + ", ".join(parts)[0].upper() + ", ".join(parts)[1:] + ".") if parts else ""
    return f"Checked {_hm(checked_at)} UK time.{tail}"


def _source_rows(sources: dict[str, SourceResult]) -> list[dict]:
    rows = []
    for sid, r in sources.items():
        name, use = SOURCE_USE.get(sid, (sid, "Signal"))
        rows.append({"name": name, "reference_period": r.reference_period or "\u2014",
                     "published_at": r.published_at or "\u2014", "retrieved_at": r.checked_at,
                     "checked_at": r.checked_at, "source_updated_at": r.source_updated_at,
                     "mode": r.mode, "use": use, "status": r.status,
                     "attribution": r.licence.attribution})
    rows.append({"name": "Carrier and port advisories", "reference_period": "\u2014",
                 "published_at": "\u2014", "retrieved_at": "\u2014", "checked_at": None,
                 "source_updated_at": None, "mode": "not_used",
                 "use": "Not used yet: reuse terms not recorded", "status": "unavailable"})
    return rows


def _finding(e: Event) -> dict:
    verb = "confirms" if e.status == "confirmed" else "reported"
    if e.status == "confirmed":
        text = f"An official notice {verb}: {e.title}"
        src = "Port or carrier notice"
    else:
        text = f"News reports (not confirmed): {e.title}"
        src = "GDELT news"
    return {"text": text, "status": e.status, "source": src, "as_of": _day(e.last_seen),
            "note": f"{e.report_count} reports, duplicates merged; {e.match_reason}",
            "urls": [e.confirmation_url] if e.confirmation_url else e.source_urls[:3]}


def _fx_series(currency: str, records: list[dict], date_from: str | None) -> list[list]:
    """The ECB rate per day from date_from on, as [date, units per EUR], for the page's chart."""
    from .exposure import ECB_FIELDS
    key = ECB_FIELDS.get(currency)
    if not key or not date_from:
        return []
    return [[r["reference_period"], r[key]] for r in sorted(records, key=lambda r: r["reference_period"])
            if r.get(key) is not None and r["reference_period"] >= date_from]


def _fx_block(fx: FxExposure, records: list[dict] | None = None) -> dict:
    block = {"status": fx.status, "source": "ECB reference rate",
             "as_of": _day(fx.date_to), "finding": fx.note,
             "reading": "This is not your bank's rate, and exchange rates say nothing about delays.",
             "action": "Request a current quote from your supplier."}
    if fx.status == "computed":
        block["eur_cost_change_pct"] = fx.eur_cost_change_pct
        # Units of the invoice currency per EUR, so the page can compare a bank's quote.
        block.update(rate_then=fx.rate_from, rate_now=fx.rate_to, date_then=fx.date_from, date_now=fx.date_to,
                     currency=fx.currency, unfixed_share=fx.unfixed_share,
                     series=_fx_series(fx.currency, records or [], fx.date_from))
    return block


def route_geo(inp: ImporterInputs, events: list[Event]) -> list[dict]:
    """One entry per typed port, origin first. event is null, "unconfirmed" or "confirmed"."""
    stops = [(inp.origin_port, "origin"), *((p, "transshipment") for p in inp.transshipment_ports),
             (inp.destination_port, "destination")]
    out = []
    for name, role in stops:
        hit = lookup(name)
        key = hit[0] if hit else name
        st = {e.status for e in events if any(m.lower() in (name.lower(), key.lower()) for m in e.matched_places)}
        ev = "confirmed" if "confirmed" in st else "unconfirmed" if st else None
        out.append({"port": name, "role": role, "locode": hit[1] if hit else None,
                    "lat": hit[2] if hit else None, "lon": hit[3] if hit else None, "event": ev})
    return out


def decide(inp: ImporterInputs, sources: dict[str, SourceResult], gdelt_records: list[dict],
           now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    lane = to_lane(inp)
    news_from, _ = news_window(inp.window_start, inp.window_end, now.date())
    events = filter_events(gdelt_records, lane, inp.window_start, inp.window_end, news_from=news_from)
    confirmed = [e for e in events if e.status == "confirmed"]
    stock = stock_exposure(inp.stock_days, inp.lead_time_days)
    ecb = sources.get("ecb_fx")
    fx = fx_exposure(inp.currency, inp.fixed_rate_share, ecb.records if ecb else [])
    covers = stock_sentence(stock)

    if confirmed and stock.shortfall:
        state = "alert"
        headline = f"Check your forwarder's ETA today: {covers[0].lower() + covers[1:]}"
        heading = f"{len(confirmed)} confirmed event{'s' if len(confirmed) > 1 else ''} and your stock exposure"
        reading = "This may delay shipments on the route you confirmed. We can't tell yet whether your shipment is affected."
        action = "Ask your forwarder for a current ETA. Consider ordering earlier."
    elif confirmed:
        state = "covered"
        headline = f"A confirmed event may affect your route. {covers}"
        heading = "Confirmed event, stock covers lead time"
        reading = covers
        action = "Ask your forwarder for a current ETA if the event lasts."
    else:
        state = "insufficient"
        headline = ABSTAIN
        heading = "Not enough evidence"
        n_rep = len(events)
        reading = (f"Checked {len(sources)} sources: {n_rep} unconfirmed report{'s' if n_rep != 1 else ''}, "
                   "no carrier or port confirmation for your route.")
        action = (f"{covers} Ask your forwarder for a current ETA." if stock.shortfall
                  else f"{covers} Ask your forwarder for a current ETA if you're unsure.")

    route = " \u2192 ".join([inp.origin_port, *inp.transshipment_ports, inp.destination_port])
    checked = now.isoformat(timespec="seconds")
    return {
        "state": state, "example": False, "question": QUESTION, "headline": headline,
        "inputs": {"importer": inp.importer, "route": route, "currency": inp.currency,
                   "hedged": inp.fixed_rate_share == 1.0, "stock_days": inp.stock_days,
                   "lead_time_days": inp.lead_time_days},
        "delay": {"heading": heading, "findings": [_finding(e) for e in (confirmed or events)[:5]],
                  "exposure": {"stock_days": inp.stock_days, "lead_time_days": inp.lead_time_days,
                               "buffer_days": stock.buffer_days, "shortfall": stock.shortfall,
                               "sentence": covers, "arithmetic": stock.arithmetic},
                  "reading": reading, "action": action},
        "fx": _fx_block(fx, ecb.records if ecb else []),
        "sources": _source_rows(sources),
        "coverage": (cov := coverage(confirmation_enabled())),
        "coverage_line": cov["line"],
        "route_geo": route_geo(inp, events),  # read by the #18 UI
        "coverage_gaps": cov["ports"],
        "checked_at": checked,
        "dates_line": dates_line(checked, sources),
    }
