"""Ship counts near a port from AISHub (https://www.aishub.net), behind a flag.

Off unless AIS_ENABLED=1 and AISHUB_USERNAME is set (AISHub gives API access to
members who share an AIS receiver feed; free, non-commercial). We only keep and
show aggregate counts per port (ships at anchor, ships moving), never names,
positions or tracks, so no individual vessel is displayed by this app.

Navigational status codes (ITU-R M.1371): 1 = at anchor, 5 = moored.
"""
from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlencode

from .base import FetchError, Licence, Loader, http_json, now_iso
from .gdelt import RateGate, _slug

API = "https://data.aishub.net/ws.php"
BOX_DEG = 0.25  # about 15 nautical miles each way: the anchorage, not just the quay
GATE = RateGate(interval_s=61.0)  # AISHub allows about one request a minute


def ais_enabled() -> bool:
    return os.environ.get("AIS_ENABLED") == "1" and bool(os.environ.get("AISHUB_USERNAME"))


def summarise(rows: list[dict]) -> dict:
    waiting = sum(1 for r in rows if r.get("NAVSTAT") == 1)
    moored = sum(1 for r in rows if r.get("NAVSTAT") == 5)
    moving = sum(1 for r in rows if r.get("NAVSTAT") not in (1, 5) and (r.get("SOG") or 0) >= 10)  # SOG in 1/10 knot
    return {"ships": len(rows), "waiting": waiting, "moored": moored, "moving": moving}


class AisPortLoader(Loader):
    source_id = "ais"
    endpoint = API
    cache_ttl_s = 900
    licence = Licence(
        name="AISHub data sharing: free for members who contribute a feed; aggregate counts only shown (terms to confirm before public display)",
        url="https://www.aishub.net/join-us",
        attribution="Ship counts: AISHub.",
    )

    def __init__(self, port: str, lat: float, lon: float, gate_wait_s: float = 0.0):
        self.port, self.lat, self.lon, self.gate_wait_s = port, lat, lon, gate_wait_s

    def cache_key(self) -> str:
        return f"ais-{_slug(self.port)}"

    def fetch(self) -> Any:
        if not GATE.acquire(self.gate_wait_s):
            raise FetchError("AISHub busy: one request a minute")
        q = {"username": os.environ.get("AISHUB_USERNAME", ""), "format": 1, "output": "json", "compress": 0,
             "latmin": self.lat - BOX_DEG, "latmax": self.lat + BOX_DEG,
             "lonmin": self.lon - BOX_DEG, "lonmax": self.lon + BOX_DEG}
        return http_json(f"{API}?{urlencode(q)}")

    def parse(self, payload: Any):
        head = payload[0] if isinstance(payload, list) and payload else {}
        if head.get("ERROR"):
            raise FetchError(f"AISHub error: {head.get('ERROR_MESSAGE', 'unknown')}")
        rows = payload[1] if len(payload) > 1 else []
        rec = {"port": self.port, **summarise(rows), "retrieved_at": now_iso()}
        return [rec], rec["retrieved_at"], None
