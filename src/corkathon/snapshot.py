"""Write a dated snapshot per source: python -m corkathon.snapshot [source_id ...]

open_meteo saves one file holding the forecast for every LANE_PORTS port; each
port's loader reads back only its own rows. A saved forecast only speaks for days
from the read date on, so an old one fades out instead of describing the past."""
from __future__ import annotations

import os
import sys

from .ports import lookup
from .sources.base import write_snapshot
from .sources.open_meteo import PortWeatherLoader
from .sources.registry import LOADERS

LANE_PORTS = [p.strip() for p in os.environ.get(
    "LANE_PORTS", "Rotterdam,Antwerp,Felixstowe,Dublin,Cork").split(",") if p.strip()]


def weather_snapshot():
    merged = None
    for port in LANE_PORTS:
        hit = lookup(port)
        if not hit:
            continue
        res = PortWeatherLoader(hit[0], hit[2], hit[3]).load_live()
        if res.status != "ok":
            print(f"open_meteo {port}: {res.status} ({res.reason})")
            continue
        if merged is None:
            merged = res
        else:
            merged.records += res.records
    return merged


def main(argv: list[str]) -> int:
    names = argv or [*LOADERS, "open_meteo"]
    for name in names:
        res = weather_snapshot() if name == "open_meteo" else LOADERS[name]().load_live()
        if res is None or res.status != "ok":
            print(f"{name}: {'unavailable' if res is None else res.status}; snapshot not written")
            continue
        print(f"{name}: ok ref={res.reference_period} -> {write_snapshot(res)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
