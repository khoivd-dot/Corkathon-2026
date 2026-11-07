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


def refresh_once() -> None:
    for port in LANE_PORTS:
        PortGdeltLoader(port).load()


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
    for sid in ("ecb_fx", "cso_trade", "comext", "met_warnings"):
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
        n = int(self.headers.get("Content-Length") or 0)
        if n > MAX_BODY:
            return self._send(413, b"too large", "text/plain")
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            return self._send(400, b'{"errors": {"_": "Send valid JSON."}}', "application/json")

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
        self._send(code, json.dumps(out, ensure_ascii=False).encode(), "application/json")


def main() -> None:
    if os.environ.get("SNAPSHOT_ONLY") != "1":
        threading.Thread(target=_refresher, daemon=True).start()
    port = int(os.environ.get("PORT", "8000"))
    print(f"listening on :{port}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
