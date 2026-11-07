"""Live ship position (aisstream.io): off by default, websocket framing, parsing, endpoint."""
import base64
import hashlib
import json
import os
import tempfile
import unittest
from unittest import mock

from corkathon import server
from corkathon.sources import aisstream as ais
from corkathon.sources.base import FetchError

POS = {"MessageType": "PositionReport",
       "MetaData": {"MMSI": 636019825, "ShipName": "MSC TEST   ", "latitude": 51.62, "longitude": -8.1,
                    "time_utc": "2026-11-07 16:20:01.123456789 +0000 UTC"},
       "Message": {"PositionReport": {"Latitude": 51.62, "Longitude": -8.1, "Sog": 12.3, "Cog": 45.4,
                                      "NavigationalStatus": 0, "UserID": 636019825}}}
STATIC = {"MessageType": "ShipStaticData", "MetaData": {"MMSI": 636019825},
          "Message": {"ShipStaticData": {"Destination": "IEORK  ", "ImoNumber": 9876543,
                                         "Eta": {"Month": 11, "Day": 8, "Hour": 6, "Minute": 0}}}}


class FakeSock:
    def __init__(self, data: bytes):
        self.data, self.sent = data, b""

    def recv(self, n):
        out, self.data = self.data[:n], self.data[n:]
        return out

    def sendall(self, b):
        self.sent += b

    def settimeout(self, t):
        pass


def server_frame(payload: bytes, opcode=1, fin=True):
    n = len(payload)
    head = bytes([(0x80 if fin else 0) | opcode])
    head += bytes([n]) if n < 126 else bytes([126]) + n.to_bytes(2, "big")
    return head + payload


class AisStreamTests(unittest.TestCase):
    def test_off_by_default(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertFalse(ais.live_enabled())
            out, code = server.vessel("636019825")
        self.assertEqual((out["enabled"], code), (False, 200))
        with mock.patch.dict(os.environ, {"AIS_LIVE_ENABLED": "1"}, clear=True):
            self.assertFalse(ais.live_enabled())  # needs a key too

    def test_mmsi_check(self):
        self.assertTrue(ais.valid_mmsi("636019825"))
        for bad in ("12345678", "1234567890", "963019825", "00301982x", ""):
            self.assertFalse(ais.valid_mmsi(bad), bad)

    def test_client_frame_is_masked_and_round_trips(self):
        f = ais.encode_frame(b'{"a":1}', mask=b"\x01\x02\x03\x04")
        self.assertEqual(f[0], 0x81)
        self.assertTrue(f[1] & 0x80)
        self.assertEqual(ais.read_frame(FakeSock(f)), (1, True, b'{"a":1}'))
        big = b"x" * 300
        self.assertEqual(ais.read_frame(FakeSock(ais.encode_frame(big)))[2], big)

    def test_handshake_checks_accept_key(self):
        with mock.patch.object(ais.os, "urandom", return_value=b"k" * 16):
            key = base64.b64encode(b"k" * 16).decode()
            acc = base64.b64encode(hashlib.sha1((key + ais.GUID).encode()).digest()).decode()
            ok = FakeSock(f"HTTP/1.1 101 Switching Protocols\r\nSec-WebSocket-Accept: {acc}\r\n\r\n".encode())
            ais.handshake(ok)
            self.assertIn(b"Sec-WebSocket-Version: 13", ok.sent)
            with self.assertRaises(FetchError):
                ais.handshake(FakeSock(b"HTTP/1.1 401 Unauthorized\r\n\r\n"))

    def test_messages_handles_ping_fragments_and_close(self):
        body = json.dumps(POS).encode()
        data = (server_frame(b"hi", opcode=9) + server_frame(body[:10], opcode=2, fin=False)
                + server_frame(body[10:], opcode=0) + server_frame(b"\x03\xe8", opcode=8))
        sock = FakeSock(data)
        got = list(ais.messages(sock, deadline=float("inf")))
        self.assertEqual(got, [POS])
        self.assertEqual(ais.read_frame(FakeSock(sock.sent)), (10, True, b"hi"))  # pong echoes the ping

    def test_error_message_raises(self):
        sock = FakeSock(server_frame(b'{"error":"Api Key Is Not Valid"}'))
        with self.assertRaises(FetchError):
            list(ais.messages(sock, deadline=float("inf")))

    def test_pick_merges_static_and_ignores_other_ships(self):
        other = json.loads(json.dumps(POS)); other["MetaData"]["MMSI"] = 1
        v = ais.pick(iter([other, STATIC, POS]), "636019825")
        self.assertEqual((v["name"], v["lat"], v["speed_kn"], v["course"], v["status"]),
                         ("MSC TEST", 51.62, 12.3, 45, "under way using engine"))
        self.assertEqual((v["destination"], v["position_at"]), ("IEORK", "2026-11-07T16:20:01+00:00"))
        self.assertIsNone(ais.pick(iter([other]), "636019825"))

    def test_endpoint_live_position_on_route(self):
        env = {"AIS_LIVE_ENABLED": "1", "AISSTREAM_API_KEY": "k", "SNAPSHOT_ONLY": "0", "SNAPSHOT": "0",
               "CACHE_DIR": tempfile.mkdtemp()}
        with mock.patch.dict(os.environ, env), mock.patch.object(ais, "stream", return_value=iter([POS])):
            out, code = server.vessel("636019825", "Cork")
        v = out["vessel"]
        self.assertEqual((code, out["status"], out["mode"], ), (200, "ok", "live"))
        self.assertEqual(v["nearest_port"], "Cork")
        self.assertEqual(v["to_port"], "Cork")
        self.assertIn("openstreetmap.org", v["map_url"])
        self.assertEqual(out["source"]["name"], "aisstream.io")

    def test_endpoint_no_position_is_said_plainly(self):
        env = {"AIS_LIVE_ENABLED": "1", "AISSTREAM_API_KEY": "k", "SNAPSHOT_ONLY": "0", "SNAPSHOT": "0",
               "CACHE_DIR": tempfile.mkdtemp(), "AIS_LIVE_WAIT_S": "3"}
        with mock.patch.dict(os.environ, env), mock.patch.object(ais, "stream", return_value=iter([])):
            out, code = server.vessel("636019825")
        self.assertEqual((code, out["status"]), (200, "unavailable"))
        self.assertNotIn("vessel", out)
        self.assertIn("open ocean", out["message"])

    def test_bad_mmsi_is_400(self):
        with mock.patch.dict(os.environ, {"AIS_LIVE_ENABLED": "1", "AISSTREAM_API_KEY": "k"}):
            self.assertEqual(server.vessel("123")[1], 400)


if __name__ == "__main__":
    unittest.main()
