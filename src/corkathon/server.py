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
from .inputs import InputError, parse_inputs
from .sources.base import REPO_ROOT
from .sources.gdelt import PortGdeltLoader
from .sources.registry import LOADERS

WEB = Path(os.environ.get("WEB_DIR", REPO_ROOT / "web"))
REFRESH_S = int(os.environ.get("REFRESH_S", "1800"))
LANE_PORTS = tuple(p.strip() for p in os.environ.get(
    "LANE_PORTS", "Rotterdam,Antwerp,Felixstowe,Dublin,Cork").split(",") if p.strip())
MAX_BODY = 8 * 1024
TYPES = {".html": "text/html; charset=utf-8", ".css": "text/css", ".js": "text/javascript",
         ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png"}
HEADERS = {"Content-Security-Policy": "default-src 'self'; img-src 'self' data:; frame-ancestors 'none'",
           "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer",
           "Cache-Control": "no-store"}


def refresh_once() -> None:
    for i, port in enumerate(LANE_PORTS):
        if i:
            time.sleep(6)  # GDELT asks for <= 1 request / 5 s
        PortGdeltLoader(port).load()


def _refresher() -> None:
    while True:
        try:
            refresh_once()
        except Exception as e:  # keep serving; the next cycle retries
            print(f"refresh failed: {type(e).__name__}", flush=True)
        time.sleep(REFRESH_S)


def answer(form: dict) -> dict:
    inp = parse_inputs(form)
    ports = [inp.origin_port, *inp.transshipment_ports, inp.destination_port]
    records: list[dict] = []
    gdelt = None
    for p in ports:  # each port read separately; cache key = port name only
        r = PortGdeltLoader(p).load()
        records += r.records
        gdelt = gdelt or r
    sources = {"gdelt": gdelt}
    for sid in ("ecb_fx", "cso_trade", "comext"):
        sources[sid] = LOADERS[sid]().load()
    return decide(inp, sources, records)


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
        n = int(self.headers.get("Content-Length") or 0)
        if n > MAX_BODY:
            return self._send(413, b"too large", "text/plain")
        try:
            form = json.loads(self.rfile.read(n) or b"{}")
            out, code = answer(form), 200
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
