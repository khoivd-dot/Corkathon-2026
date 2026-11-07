"""Static, checked-in port coordinates for the route map. No runtime fetch.

Codes are UN/LOCODE. Coordinates are approximate port-area positions (2 dp),
hand-entered for display only; they are not used in any calculation.
"""
from __future__ import annotations

import re

# name -> (UN/LOCODE, lat, lon)
PORTS: dict[str, tuple[str, float, float]] = {
    "Cork": ("IEORK", 51.84, -8.30), "Ringaskiddy": ("IEORK", 51.83, -8.32),
    "Dublin": ("IEDUB", 53.35, -6.21), "Rotterdam": ("NLRTM", 51.95, 4.14),
    "Antwerp": ("BEANR", 51.27, 4.33), "Felixstowe": ("GBFXT", 51.96, 1.33),
    "Southampton": ("GBSOU", 50.90, -1.43), "Liverpool": ("GBLIV", 53.45, -3.02),
    "Hamburg": ("DEHAM", 53.54, 9.97), "Bremerhaven": ("DEBRV", 53.56, 8.55),
    "Le Havre": ("FRLEH", 49.48, 0.11), "Algeciras": ("ESALG", 36.13, -5.44),
    "Valencia": ("ESVLC", 39.44, -0.32), "Piraeus": ("GRPIR", 37.94, 23.63),
    "Port Said": ("EGPSD", 31.26, 32.30), "Jebel Ali": ("AEJEA", 25.01, 55.06),
    "Colombo": ("LKCMB", 6.95, 79.84), "Nhava Sheva": ("INNSA", 18.95, 72.95),
    "Singapore": ("SGSIN", 1.26, 103.84), "Shanghai": ("CNSHA", 31.23, 121.49),
    "Ningbo": ("CNNGB", 29.87, 121.55), "Shenzhen": ("CNSZX", 22.54, 114.06),
    "Hong Kong": ("HKHKG", 22.29, 114.16), "Busan": ("KRPUS", 35.10, 129.04),
    "Ho Chi Minh City": ("VNSGN", 10.77, 106.71), "Santos": ("BRSSZ", -23.96, -46.33),
    "New York": ("USNYC", 40.67, -74.04), "Savannah": ("USSAV", 32.08, -81.09),
    "Los Angeles": ("USLAX", 33.74, -118.26), "Mombasa": ("KEMBA", -4.06, 39.67),
    "Durban": ("ZADUR", -29.87, 31.03),
}
_KEYS = {k.lower(): k for k in PORTS}


def lookup(name: str) -> tuple[str, str, float, float] | None:
    """Match a typed port name, ignoring a bracketed terminal, e.g. 'Cork (Ringaskiddy)'."""
    n = re.sub(r"\s*\(.*\)\s*$", "", name or "").strip().lower()
    k = _KEYS.get(n)
    return (k, *PORTS[k]) if k else None
