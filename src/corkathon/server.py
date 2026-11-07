"""Web server for Render. Standard library only.

GET  /healthz      -> 200 "ok"
POST /api/answer   -> decision JSON for the form fields (held in memory only)
POST /api/parse    -> plain-English query parsed into form fields and chips
POST /api/timing   -> timing block only for as_of slider, using holidays & lead time
GET  /*            -> static files from web/ (the #8 answer-card UI)

A background thread refreshes the per-port GDELT cache every REFRESH_S seconds
(default 1800) for the public lane ports. Nothing a user types is written to disk
or logged: request bodies are never logged and the cache is keyed by port only.
"""
from __future__ import annotations

import json
import os
import threading
import time
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .decision import decide
from .inputs import InputError, parse_inputs
from .parse import parse_query
from .ports import lookup
from .sources.ais import AisPortLoader, ais_enabled
from .sources.base import REPO_ROOT, SourceResult, now_iso
from .sources.gdelt import PortGdeltLoader
from .sources.holidays import HolidaysLoader, country_for_port, load_holidays_for_country
from .sources.met_warnings import warnings_for_port
from .sources.open_meteo import PortWeatherLoader, port_sentence, rough_days, weather_enabled
from .sources.registry import LOADERS
from .timing import compute_timing

WEB = Path(os.environ.get("WEB_DIR", REPO_ROOT / "web"))
REFRESH_S = int(os.environ.get("REFRESH_S", "1800"))
LANE_PORTS = tuple(p.strip() for p in os.environ.get(
    "LANE_PORTS", "Rotterdam,Antwerp,Felixstowe,Dublin,Cork").split(",") if p.strip())
MAX_BODY = 8 * 1024
TYPES = {".html": "text/html; charset=utf-8", ".css": "text/css", ".js": "text/javascript",
         ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png", ".webp": "image/webp",
         ".ttf": "font/ttf", ".woff2": "font/woff2", ".txt": "text/plain; charset=utf-8"}
HEADERS = {"Content-Security-Policy": "default-src 'self'; img-src 'self' data:; frame-ancestors 'none'",
           "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer",
           "Cache-Control": "no-store"}

REQUEST_GATE_WAIT_S = float(os.environ.get("REQUEST_GATE_WAIT_S", "6"))
_RANK = {"ok": 0, "snapshot": 1, "stale": 2, "unavailable": 3}


CONTEXT_SOURCES = ("ecb_fx", "cso_trade", "comext")


def refresh_once() -> None:
    """Keep every shared source warm, so a user's answer reads the cache instead of
    waiting on a live fetch when a TTL runs out (ECB daily, CSO and Comext monthly).
    Each load() returns the cached copy while it's fresh, so this costs nothing then."""
    for sid in CONTEXT_SOURCES:
        LOADERS[sid]().load()
    for port in LANE_PORTS:  # GATE in sources/gdelt.py spaces the calls >= 5 s apart
        PortGdeltLoader(port).load()
    if weather_enabled():
        for port in LANE_PORTS:
            hit = lookup(port)
            if hit:
                PortWeatherLoader(hit[0], hit[2], hit[3]).load()


def news_ports(typed: list[str]) -> tuple[list[str], list[str]]:
    known: list[str] = []
    unknown: list[str] = []
    for name in typed:
        hit = lookup(name)
        if hit and hit[0] not in known:
            known.append(hit[0])
        elif not hit and name not in unknown:
            unknown.append(name)
    return known, unknown


def _refresher() -> None:
    while True:
        try:
            refresh_once()
        except Exception as e:
            print(f"refresh failed: {type(e).__name__}", flush=True)
        time.sleep(REFRESH_S)


def answer(form: dict) -> dict:
    inp = parse_inputs(form)
    known, unknown = news_ports([inp.origin_port, *inp.transshipment_ports, inp.destination_port])
    records: list[dict] = []
    per_port = []
    gdelt = None
    for p in known:
        r = PortGdeltLoader(p, gate_wait_s=REQUEST_GATE_WAIT_S).load()
        records += r.records
        per_port.append({"port": p, "status": r.status, "mode": r.mode, "checked_at": r.checked_at})
        if gdelt is None or _RANK.get(r.status, 9) > _RANK.get(gdelt.status, 9):
            gdelt = r
    sources = {"gdelt": gdelt or PortGdeltLoader(inp.destination_port).load_snapshot("no known port")}
    for sid in (*CONTEXT_SOURCES, "met_warnings"):
        if sid in LOADERS:
            sources[sid] = LOADERS[sid]().load()

    # Load holidays for origin and destination countries
    origin_cc = country_for_port(inp.origin_port) or "CN"
    dest_cc = country_for_port(inp.destination_port) or "IE"
    hols_records = load_holidays_for_country(origin_cc) + load_holidays_for_country(dest_cc)
    sources["holidays"] = SourceResult(
        source_id="holidays",
        endpoint="https://date.nager.at/api/v3/PublicHolidays/{year}/{CC}",
        licence=HolidaysLoader.licence,
        status="ok",
        checked_at=now_iso(),
        records=hols_records,
    )

    out = decide(inp, sources, records)
    out["news_ports"] = {"checked": per_port, "unknown": unknown}
    if weather_enabled():
        out["weather"] = weather_block(known)
        w = out["weather"]
        if w["checked_at"]:
            out["sources"].append({"name": "Open-Meteo weather forecast", "reference_period": w["reference_period"],
                                   "published_at": "\u2014", "retrieved_at": w["checked_at"],
                                   "checked_at": w["checked_at"], "source_updated_at": w["checked_at"],
                                   "mode": w["mode"], "use": "Signal only: forecast wind and waves at each port",
                                   "status": w["status"], "attribution": PortWeatherLoader.licence.attribution})
    if ais_enabled():
        out["ais"] = ais_counts(known)
        if out["ais"]["ports"]:
            out["sources"].append({
                "name": "AISHub ship counts", "reference_period": "Last 15 minutes",
                "published_at": "\u2014", "retrieved_at": out["ais"]["checked_at"],
                "checked_at": out["ais"]["checked_at"], "source_updated_at": out["ais"]["checked_at"],
                "mode": out["ais"]["mode"], "use": "Context only: counts near each port",
                "status": out["ais"]["status"]
            })
    return out


def timing_only(body: dict) -> tuple[dict, int]:
    today = date.today()
    as_of_raw = body.get("as_of")
    if not as_of_raw:
        as_of_date = today
    else:
        try:
            as_of_date = date.fromisoformat(str(as_of_raw)[:10])
        except (ValueError, TypeError):
            return {"error": "Enter a date like 2026-12-20."}, 400

    if not (today <= as_of_date <= today + timedelta(days=400)):
        return {"error": "The date must fall within today and 400 days from today."}, 400

    origin_port = str(body.get("origin_port") or "").strip()
    dest_port = str(body.get("destination_port") or "").strip()
    origin_cc = country_for_port(origin_port) or "CN"
    dest_cc = country_for_port(dest_port) or "IE"

    try:
        stock_days = int(body.get("stock_days") or 0)
        lead_days = int(body.get("lead_days") or body.get("lead_time_days") or 1)
    except (ValueError, TypeError):
        return {"error": "Stock days and lead time must be whole numbers."}, 400

    hols = load_holidays_for_country(origin_cc) + load_holidays_for_country(dest_cc)

    notices = []
    if "met_warnings" in LOADERS:
        met_res = LOADERS["met_warnings"]().load()
        if met_res.records and dest_port:
            notices = warnings_for_port(met_res.records, dest_port)

    timing = compute_timing(
        stock_days=stock_days,
        lead_days=lead_days,
        origin_country=origin_cc,
        dest_country=dest_cc,
        holidays=hols,
        notices=notices,
        as_of=as_of_date,
        origin_port=origin_port,
        dest_port=dest_port,
    )
    return timing, 200


def weather_block(ports: list[str], today=None) -> dict:
    """Next-7-day wind and waves at each known port on the route, one call and one
    cache entry per public port. Only rough days are put into words; a port with no
    forecast is named as unchecked, never described as calm."""
    from datetime import datetime, timezone
    today = today or datetime.now(timezone.utc).date()
    lines, rough_ports, calm, missing = [], [], [], []
    checked, mode, status, ref = None, "live", "ok", None
    for p in ports:
        hit = lookup(p)
        if not hit:
            continue
        r = PortWeatherLoader(hit[0], hit[2], hit[3]).load()
        future = [x for x in r.records if x.get("date", "") >= today.isoformat()]
        if r.status == "unavailable" or not future:
            missing.append(hit[0])
            continue
        checked = max(checked or r.checked_at, r.checked_at)
        ref = min(ref or future[0]["date"], future[0]["date"])
        if r.mode == "fallback":
            mode, status = "fallback", r.status
        bad = rough_days(future, today)
        if bad:
            rough_ports.append(hit[0]); lines.append(port_sentence(hit[0], bad))
        else:
            calm.append(hit[0])
    if calm:
        lines.append(f"No gale-force gusts or very rough seas forecast at {_join(calm)} in the next 7 days. "
                     "Forecasts change, and they say nothing about delays further ahead.")
    if missing:
        lines.append(f"We have no weather forecast for {_join(missing)} right now.")
    return {"lines": lines, "rough_ports": rough_ports, "checked_at": checked, "mode": mode, "status": status,
            "reference_period": f"Next 7 days from {ref}" if ref else None,
            "attribution": PortWeatherLoader.licence.attribution, "url": "https://open-meteo.com/"}


def _join(xs: list[str]) -> str:
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]


def ais_counts(ports: list[str]) -> dict:
    rows, checked, mode, status = [], None, "live", "ok"
    for p in ports:
        hit = lookup(p)
        if not hit:
            continue
        r = AisPortLoader(p, hit[2], hit[3]).load()
        if r.records:
            rows.append({k: r.records[0][k] for k in ("port", "waiting", "moored", "moving")})
            checked = max(checked or r.checked_at, r.checked_at)
        if r.mode == "fallback":
            mode, status = "fallback", r.status
    return {"ports": rows, "checked_at": checked, "mode": mode, "status": status,
            "note": "Counts within about 15 nautical miles of each port, from AISHub. A queue at anchor can mean congestion, or just normal waiting."}


class Handler(BaseHTTPRequestHandler):
    server_version = "corkathon"

    def log_message(self, fmt, *args):
        print(f"{self.command} {self.path.split('?')[0]} {args[1] if len(args) > 1 else ''}", flush=True)

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in HEADERS.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/healthz":
            return self._send(200, b"ok", "text/plain")
        rel = "index.html" if path in ("", "/") else path.lstrip("/")
        f = (WEB / rel).resolve()
        if WEB.resolve() not in f.parents or not f.is_file():
            return self._send(404, b"not found", "text/plain")
        self._send(200, f.read_bytes(), TYPES.get(f.suffix, "application/octet-stream"))

    def do_POST(self):
        path = self.path.split("?")[0]
        if path not in ("/api/answer", "/api/parse", "/api/timing"):
            return self._send(404, b"not found", "text/plain")
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = -1
        if n < 0:
            return self._send(400, b"bad length", "text/plain")
        if n > MAX_BODY:
            return self._send(413, b"too large", "text/plain")
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
            if not isinstance(body, dict):
                raise ValueError("not an object")
        except ValueError:
            return self._send(400, b'{"errors": {"_": "Send the form as JSON."}}', "application/json")

        if path == "/api/parse":
            q = str(body.get("q", ""))
            out = parse_query(q)
            return self._send(200, json.dumps(out, ensure_ascii=False).encode(), "application/json")

        if path == "/api/timing":
            out, code = timing_only(body)
            return self._send(code, json.dumps(out, ensure_ascii=False).encode(), "application/json")

        # /api/answer
        try:
            out, code = answer(body), 200
        except InputError as e:
            out, code = {"errors": e.errors}, 400
        except ValueError:
            out, code = {"errors": {"_": "Send the form as JSON."}}, 400
        except Exception as e:  # noqa: BLE001 - answer with JSON, never drop the connection
            print(f"answer failed: {type(e).__name__}", flush=True)  # type only: no user input in logs
            out, code = {"errors": {"_": "Something went wrong on our side. Try again in a minute."}}, 500
        self._send(code, json.dumps(out, ensure_ascii=False).encode(), "application/json")


def main() -> None:
    if os.environ.get("SNAPSHOT_ONLY") != "1":
        threading.Thread(target=_refresher, daemon=True).start()
    port = int(os.environ.get("PORT", "8000"))
    print(f"listening on :{port}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
