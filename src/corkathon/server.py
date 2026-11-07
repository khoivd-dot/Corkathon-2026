"""Web server for Render. Standard library only.

GET  /healthz      -> 200 "ok"
POST /api/answer   -> decision JSON for the form fields (held in memory only)
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
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .decision import decide
from .ports import lookup
from .inputs import InputError, parse_inputs
from .sources.base import REPO_ROOT
from .sources.ais import AisPortLoader, ais_enabled
from .sources.gdelt import PortGdeltLoader
from .sources.registry import LOADERS

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


def news_ports(typed: list[str]) -> tuple[list[str], list[str]]:
    """Split typed ports into ones we search news for (canonical names, deduplicated)
    and ones we don't recognise. Only known public port names ever reach GDELT or
    the cache, so a typo or free text never becomes a live query or a cache file."""
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
        except Exception as e:  # keep serving; the next cycle retries
            print(f"refresh failed: {type(e).__name__}", flush=True)
        time.sleep(REFRESH_S)


def answer(form: dict) -> dict:
    inp = parse_inputs(form)
    known, unknown = news_ports([inp.origin_port, *inp.transshipment_ports, inp.destination_port])
    records: list[dict] = []
    per_port = []
    gdelt = None
    for p in known:  # each port read separately; cache key = port name only
        r = PortGdeltLoader(p, gate_wait_s=REQUEST_GATE_WAIT_S).load()
        records += r.records
        per_port.append({"port": p, "status": r.status, "mode": r.mode, "checked_at": r.checked_at})
        # The news row reports the least fresh port, so a fallback is never hidden.
        if gdelt is None or _RANK.get(r.status, 9) > _RANK.get(gdelt.status, 9):
            gdelt = r
    sources = {"gdelt": gdelt or PortGdeltLoader(inp.destination_port).load_snapshot("no known port")}
    for sid in CONTEXT_SOURCES:
        sources[sid] = LOADERS[sid]().load()
    out = decide(inp, sources, records)
    out["news_ports"] = {"checked": per_port, "unknown": unknown}
    if ais_enabled():
        out["ais"] = ais_counts(known)
        if out["ais"]["ports"]:
            out["sources"].append({"name": "AISHub ship counts", "reference_period": "Last 15 minutes",
                                   "published_at": "\u2014", "retrieved_at": out["ais"]["checked_at"],
                                   "checked_at": out["ais"]["checked_at"], "source_updated_at": out["ais"]["checked_at"],
                                   "mode": out["ais"]["mode"], "use": "Context only: counts near each port",
                                   "status": out["ais"]["status"]})
    return out


def ais_counts(ports: list[str]) -> dict:
    """Aggregate ship counts near each known port. Never names or positions."""
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

    def log_message(self, fmt, *args):  # method and path only; never bodies or queries
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
        if self.path.split("?")[0] != "/api/answer":
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
            form = json.loads(self.rfile.read(n) or b"{}")
            if not isinstance(form, dict):
                raise ValueError("not an object")
            out, code = answer(form), 200
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
