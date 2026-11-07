"""Live position of one ship from aisstream.io, behind a flag.

Off unless AIS_LIVE_ENABLED=1 and AISSTREAM_API_KEY is set. aisstream.io is a free
websocket feed of terrestrial AIS (shore receivers); the key comes from signing in
at https://aisstream.io with GitHub. Their docs ask that the key stays on the
server, so the browser only ever talks to /api/vessel.

One lookup = one short websocket: subscribe to a single MMSI, wait up to
AIS_LIVE_WAIT_S seconds (default 25) for its next position report, then close.
A ship mid-ocean is out of range of shore receivers, so "no position heard" is a
normal answer, not an error we hide. Results are cached per MMSI for 5 minutes.

Stdlib only: a minimal RFC 6455 client (TLS, handshake, masked text frame out,
unmasked frames in, ping -> pong). Nothing a user types is logged; the cache key
is the MMSI, a public ship identifier, never a person.
"""
from __future__ import annotations

import base64
import hashlib
import json
import math
import os
import socket
import ssl
import struct
import threading
import time
from typing import Any, Iterator

from ..ports import PORTS
from .base import USER_AGENT, FetchError, Licence, Loader, now_iso

HOST, PATH = "stream.aisstream.io", "/v0/stream"
ENDPOINT = f"wss://{HOST}{PATH}"
GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
TYPES = ("PositionReport", "StandardClassBPositionReport", "ExtendedClassBPositionReport", "ShipStaticData")
_SLOTS = threading.BoundedSemaphore(2)  # at most two open sockets per server, so one user can't hog the key

# ITU-R M.1371 navigational status, in words a non-sailor reads.
NAVSTAT = {0: "under way using engine", 1: "at anchor", 2: "not under command", 3: "restricted in how it can move",
           4: "constrained by its draught", 5: "moored", 6: "aground", 7: "fishing", 8: "under way sailing"}


def live_enabled() -> bool:
    return os.environ.get("AIS_LIVE_ENABLED") == "1" and bool(os.environ.get("AISSTREAM_API_KEY"))


def wait_s() -> float:
    try:
        return max(3.0, min(60.0, float(os.environ.get("AIS_LIVE_WAIT_S", "25"))))
    except ValueError:
        return 25.0


def valid_mmsi(s: str) -> bool:
    """Ships carry a 9-digit MMSI starting 2-7 (country prefix). Others are coast stations, SAR, AtoN."""
    return len(s) == 9 and s.isdigit() and s[0] in "234567"


# ---------- websocket (RFC 6455, client side) ----------

def _recv_exact(sock, n: int) -> bytes:
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise FetchError("aisstream closed the connection")
        buf += chunk
    return buf


def encode_frame(payload: bytes, opcode: int = 1, mask: bytes | None = None) -> bytes:
    """A single final client frame; clients must mask (RFC 6455 5.3)."""
    mask = mask if mask is not None else os.urandom(4)
    n = len(payload)
    head = bytes([0x80 | opcode])
    if n < 126:
        head += bytes([0x80 | n])
    elif n < 65536:
        head += bytes([0x80 | 126]) + struct.pack("!H", n)
    else:
        head += bytes([0x80 | 127]) + struct.pack("!Q", n)
    return head + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(payload))


def read_frame(sock) -> tuple[int, bool, bytes]:
    b0, b1 = _recv_exact(sock, 2)
    n = b1 & 0x7F
    if n == 126:
        n = struct.unpack("!H", _recv_exact(sock, 2))[0]
    elif n == 127:
        n = struct.unpack("!Q", _recv_exact(sock, 8))[0]
    if n > 4_000_000:
        raise FetchError("aisstream frame too large")
    mask = _recv_exact(sock, 4) if b1 & 0x80 else None
    data = _recv_exact(sock, n) if n else b""
    if mask:
        data = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
    return b0 & 0x0F, bool(b0 & 0x80), data


def handshake(sock, host: str = HOST, path: str = PATH) -> None:
    key = base64.b64encode(os.urandom(16)).decode()
    sock.sendall((f"GET {path} HTTP/1.1\r\nHost: {host}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                  f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\nUser-Agent: {USER_AGENT}\r\n\r\n").encode())
    head = b""
    while b"\r\n\r\n" not in head:
        chunk = sock.recv(1024)
        if not chunk:
            raise FetchError("aisstream closed during handshake")
        head += chunk
        if len(head) > 16384:
            raise FetchError("aisstream handshake too long")
    status = head.split(b"\r\n", 1)[0]
    if b" 101" not in status:
        raise FetchError(f"aisstream refused the connection: {status[:60].decode(errors='replace')}")
    want = base64.b64encode(hashlib.sha1((key + GUID).encode()).digest())
    if want.lower() not in head.lower():
        raise FetchError("aisstream handshake accept key mismatch")


def messages(sock, deadline: float) -> Iterator[dict]:
    """Yield decoded JSON messages until the deadline or the server closes."""
    parts: list[bytes] = []
    while True:
        left = deadline - time.monotonic()
        if left <= 0:
            return
        sock.settimeout(left)
        try:
            op, fin, data = read_frame(sock)
        except (socket.timeout, TimeoutError):
            return
        if op == 8:  # close
            reason = data[2:].decode(errors="replace") if len(data) > 2 else ""
            if reason:
                raise FetchError(f"aisstream closed: {reason[:120]}")
            return
        if op == 9:  # ping
            sock.sendall(encode_frame(data, opcode=10))
            continue
        if op == 10:
            continue
        parts.append(data)
        if not fin:
            continue
        raw, parts = b"".join(parts), []
        try:
            msg = json.loads(raw)
        except ValueError:
            continue
        if isinstance(msg, dict) and msg.get("error"):
            raise FetchError(f"aisstream error: {str(msg['error'])[:120]}")
        if isinstance(msg, dict):
            yield msg


def stream(subscribe: dict, wait: float) -> Iterator[dict]:
    """Open the socket, subscribe (within aisstream's 3 s limit), yield messages."""
    ctx = ssl.create_default_context()
    try:
        raw = socket.create_connection((HOST, 443), timeout=10)
    except OSError as e:
        raise FetchError(f"network: {e}") from e
    with ctx.wrap_socket(raw, server_hostname=HOST) as sock:
        handshake(sock)
        sock.sendall(encode_frame(json.dumps(subscribe).encode()))
        yield from messages(sock, time.monotonic() + wait)
        try:
            sock.sendall(encode_frame(struct.pack("!H", 1000), opcode=8))
        except OSError:
            pass


# ---------- position, in words ----------

def nm_between(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2, dl = math.radians(lat1), math.radians(lat2), math.radians(lon2 - lon1)
    c = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 3440.065 * 2 * math.asin(min(1.0, math.sqrt(c)))


def nearest_port(lat: float, lon: float) -> tuple[str, float]:
    seen: set[str] = set()
    main = [(k, v) for k, v in PORTS.items() if not (v[0] in seen or seen.add(v[0]))]  # Cork, not its terminal
    name, (_, plat, plon) = min(main, key=lambda kv: nm_between(lat, lon, kv[1][1], kv[1][2]))
    return name, nm_between(lat, lon, plat, plon)


def _iso(t: str | None) -> str | None:
    """aisstream time_utc '2026-11-07 16:20:01.123456789 +0000 UTC' -> ISO 8601 UTC, seconds."""
    if not t:
        return None
    return t[:19].replace(" ", "T") + "+00:00" if len(t) >= 19 and t[4] == "-" else None


def pick(msgs: Iterator[dict], mmsi: str) -> dict | None:
    """First position report for this MMSI; keep name/destination/ETA from static data if seen first."""
    static: dict[str, Any] = {}
    for m in msgs:
        meta = m.get("MetaData") or {}
        if str(meta.get("MMSI", "")) != mmsi:
            continue
        kind = m.get("MessageType")
        body = (m.get("Message") or {}).get(kind) or {}
        if kind == "ShipStaticData":
            eta = body.get("Eta") or {}
            static = {"destination": (body.get("Destination") or "").strip() or None,
                      "imo": body.get("ImoNumber") or None,
                      "eta": eta if eta.get("Month") else None}
            continue
        lat, lon = body.get("Latitude", meta.get("latitude")), body.get("Longitude", meta.get("longitude"))
        if lat is None or lon is None or abs(lat) > 90 or abs(lon) > 180:
            continue  # 91/181 = "not available" in AIS
        sog = body.get("Sog")
        return {"mmsi": mmsi, "name": (meta.get("ShipName") or "").strip() or None,
                "lat": round(float(lat), 4), "lon": round(float(lon), 4),
                "speed_kn": None if sog is None or sog >= 102.3 else round(float(sog), 1),
                "course": None if body.get("Cog") is None or body["Cog"] >= 360 else round(float(body["Cog"])),
                "status": NAVSTAT.get(body.get("NavigationalStatus")),
                "position_at": _iso(meta.get("time_utc")) or now_iso(), **static}
    return None


class VesselLoader(Loader):
    source_id = "aisstream"
    endpoint = ENDPOINT
    cache_ttl_s = 300
    licence = Licence(
        name="aisstream.io free API (beta, no SLA, no formal terms); AIS is a public broadcast",
        url="https://aisstream.io",
        attribution="Ship position: aisstream.io (terrestrial AIS)",
    )

    def __init__(self, mmsi: str):
        self.mmsi = mmsi

    def cache_key(self) -> str:
        return f"aisstream-{self.mmsi}"

    def fetch(self) -> Any:
        if not _SLOTS.acquire(timeout=5):
            raise FetchError("busy: two ship lookups already running, try again in a minute")
        try:
            sub = {"APIKey": os.environ.get("AISSTREAM_API_KEY", ""),
                   "BoundingBoxes": [[[-90, -180], [90, 180]]],
                   "FiltersShipMMSI": [self.mmsi], "FilterMessageTypes": list(TYPES)}
            hit = pick(stream(sub, wait_s()), self.mmsi)
        finally:
            _SLOTS.release()
        if not hit:
            raise FetchError(f"no position heard in {wait_s():.0f} s")
        return hit

    def parse(self, payload: Any):
        return [payload], None, payload.get("position_at")

    def load_snapshot(self, reason: str | None = None):
        # No dated snapshots for single ships: say plainly that we have nothing.
        return self._result("unavailable", mode="fallback", reason=reason or "no position")
