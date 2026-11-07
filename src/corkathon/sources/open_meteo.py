"""Open-Meteo port weather: the next 7 days of wind gusts and wave height at a port.

The only source that looks ahead. News and trade figures describe the past; a gale
forecast at the destination port says something about next week. It is still a
forecast, not a delay: the answer says "may" and never changes the answer state.

Endpoints (no key for non-commercial use, which this showcase is):
- https://api.open-meteo.com/v1/forecast  daily wind_speed_10m_max, wind_gusts_10m_max (km/h)
- https://marine-api.open-meteo.com/v1/marine  daily wave_height_max (m); null on land
  or in sheltered harbours, which we report as "no wave forecast", not as calm.

Licence (checked 2026-11-07, https://open-meteo.com/en/licence and /en/terms): data
under CC BY 4.0; free for non-commercial use without ads or subscriptions; credit
Open-Meteo with a link next to the data. Marine data is "not suitable for coastal
navigation"; we only summarise it. Limits: 600 calls/min, 10,000/day.

Privacy: one public port per call and per cache entry (lat/lon from the static
table in ports.py). A user's combined route never reaches the network or the cache.
"""
from __future__ import annotations

import json
import os
from datetime import date
from typing import Any
from urllib.parse import urlencode

from .base import FetchError, Licence, Loader, http_get, now_iso
from .gdelt import _slug

FORECAST = "https://api.open-meteo.com/v1/forecast"
MARINE = "https://marine-api.open-meteo.com/v1/marine"
DAYS = 7
TIMEOUT_S = 5.0  # weather is extra context: never hold an answer for long
# Thresholds for "rough" (documented, not tuned): gusts of 75 km/h are gale force
# (Beaufort 9 starts at about 75 km/h); a 4 m significant wave height is "very rough".
GUST_KMH = 75.0
WAVE_M = 4.0


def weather_enabled() -> bool:
    """On unless WEATHER_ENABLED=0."""
    return os.environ.get("WEATHER_ENABLED", "1") != "0"


def _json(url: str) -> Any:
    raw = http_get(url, timeout=TIMEOUT_S)
    try:
        return json.loads(raw)
    except ValueError as e:
        raise FetchError(f"not JSON: {raw[:120]!r}") from e


class PortWeatherLoader(Loader):
    source_id = "open_meteo"
    endpoint = FORECAST
    cache_ttl_s = 3 * 3600  # forecasts update a few times a day
    licence = Licence(
        name="Open-Meteo: CC BY 4.0, free for non-commercial use without ads or subscriptions (checked 2026-11-07)",
        url="https://open-meteo.com/en/licence",
        attribution="Weather data by Open-Meteo.com (CC BY 4.0).",
    )

    def __init__(self, port: str, lat: float, lon: float):
        self.port, self.lat, self.lon = port, round(lat, 2), round(lon, 2)

    def cache_key(self) -> str:
        return f"weather-{_slug(self.port)}"

    def urls(self) -> tuple[str, str]:
        common = {"latitude": self.lat, "longitude": self.lon, "timezone": "UTC", "forecast_days": DAYS}
        wind = urlencode({**common, "daily": "wind_speed_10m_max,wind_gusts_10m_max", "wind_speed_unit": "kmh"})
        wave = urlencode({**common, "daily": "wave_height_max"})
        return f"{FORECAST}?{wind}", f"{MARINE}?{wave}"

    def fetch(self) -> Any:
        wind_url, wave_url = self.urls()
        wind = _json(wind_url)
        try:  # waves are optional: the marine model has no cell for some harbours
            wave = _json(wave_url)
        except FetchError:
            wave = None
        return {"wind": wind, "wave": wave}

    def parse(self, payload: Any):
        daily = (payload.get("wind") or {}).get("daily") or {}
        days = daily.get("time") or []
        if not days:
            raise FetchError("no daily forecast in response")
        gusts = daily.get("wind_gusts_10m_max") or [None] * len(days)
        winds = daily.get("wind_speed_10m_max") or [None] * len(days)
        wave_daily = ((payload.get("wave") or {}).get("daily") or {})
        waves = dict(zip(wave_daily.get("time") or [], wave_daily.get("wave_height_max") or []))
        made = now_iso()
        recs = [{"port": self.port, "date": d, "gust_max_kmh": g, "wind_max_kmh": w,
                 "wave_max_m": waves.get(d), "retrieved_at": made}
                for d, g, w in zip(days, gusts, winds)]
        # reference_period: the first forecast day; published_at unknown (Open-Meteo
        # doesn't return the model run time), so we don't invent one.
        return recs, days[0], None

    def load_snapshot(self, reason: str | None = None):
        """A saved snapshot holds several ports: keep only this port's rows."""
        res = super().load_snapshot(reason)
        res.records = [r for r in res.records if r.get("port") == self.port]
        if not res.records and res.status == "snapshot":
            res.status, res.reason = "unavailable", f"no saved forecast for {self.port}"
        return res


def _day(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d.strftime('%a')} {d.day} {d.strftime('%b')}"


def rough_days(records: list[dict], today: date) -> list[dict]:
    """Forecast days from today on with gale-force gusts or very rough seas.
    Days before today are dropped, so an old saved forecast can't speak for this week."""
    out = []
    for r in records:
        if r.get("date", "") < today.isoformat():
            continue
        g, w = r.get("gust_max_kmh"), r.get("wave_max_m")
        if (g is not None and g >= GUST_KMH) or (w is not None and w >= WAVE_M):
            out.append(r)
    return out


def port_sentence(port: str, rough: list[dict]) -> str:
    """One plain sentence for one port. Wording: 'may', never a prediction of delay."""
    worst = max(rough, key=lambda r: ((r.get("gust_max_kmh") or 0) / GUST_KMH, (r.get("wave_max_m") or 0) / WAVE_M))
    bits = []
    if worst.get("gust_max_kmh") is not None and worst["gust_max_kmh"] >= GUST_KMH:
        bits.append(f"gusts up to {round(worst['gust_max_kmh'])} km/h")
    if worst.get("wave_max_m") is not None and worst["wave_max_m"] >= WAVE_M:
        bits.append(f"waves up to {worst['wave_max_m']:.1f} m")
    days = ", ".join(_day(r["date"]) for r in rough[:3]) + (" and later" if len(rough) > 3 else "")
    return (f"Rough weather forecast at {port} on {days} ({' and '.join(bits)}). "
            "Weather like this can slow port work, so ships there may be delayed.")
