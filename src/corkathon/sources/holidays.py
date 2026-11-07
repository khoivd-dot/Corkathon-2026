"""Public holidays from Nager.Date.

Licence:
Nager.Date, MIT licence (https://date.nager.at).
Provides public holidays for origin, transshipment, and Irish ports.
Country codes are derived from the first 2 letters of UN/LOCODE in ports.py.
Only global: true holidays are retained.
"""
from __future__ import annotations

import os
from typing import Any

from ..ports import lookup
from .base import Licence, Loader, SourceResult, http_json, latest_snapshot, json

WEEK = 7 * 86400


def country_for_port(port_name: str) -> str | None:
    """Return ISO 2-letter country code for a port name from UN/LOCODE prefix in ports.py."""
    if not port_name:
        return None
    hit = lookup(port_name)
    if hit and hit[1] and len(hit[1]) >= 2:
        return hit[1][:2].upper()
    return None


class HolidaysLoader(Loader):
    source_id = "holidays"
    cache_ttl_s = WEEK  # 7 days cache per country and year
    licence = Licence(
        name="Nager.Date public holidays (MIT)",
        url="https://date.nager.at",
        attribution="Source: Nager.Date",
    )

    def __init__(self, country: str = "IE", year: int = 2026):
        self.country = country.upper()
        self.year = int(year)
        self.endpoint = f"https://date.nager.at/api/v3/PublicHolidays/{self.year}/{self.country}"

    def cache_key(self) -> str:
        return f"holidays_{self.country}_{self.year}"

    def fetch(self) -> Any:
        return http_json(self.endpoint)

    def parse(self, payload: Any):
        if not isinstance(payload, list):
            raise ValueError(f"expected list of holidays, got {type(payload).__name__}")

        records: list[dict[str, Any]] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            # Keep only global: true holidays
            if item.get("global") is not True:
                continue
            records.append({
                "country": str(item.get("countryCode") or self.country).upper(),
                "date": str(item.get("date")),
                "name": str(item.get("name")),
                "global": True,
            })
        records.sort(key=lambda r: r["date"])
        return records, str(self.year), None

    def load_snapshot(self, reason: str | None = None) -> SourceResult:
        path = latest_snapshot(self.source_id, os.environ.get("SNAPSHOT_DATE"))
        if path is None:
            return self._result("unavailable", mode="fallback", reason=(reason or "") + " | no snapshot")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            base_res = SourceResult.from_dict(raw)
            # Filter records for requested country and year
            filtered = [
                r for r in base_res.records
                if r.get("country") == self.country and str(r.get("date", "")).startswith(str(self.year))
            ]
            return SourceResult(
                source_id=self.source_id,
                endpoint=self.endpoint,
                licence=self.licence,
                status="snapshot",
                mode="fallback",
                reference_period=str(self.year),
                published_at=None,
                source_updated_at=base_res.source_updated_at or str(self.year),
                checked_at=base_res.checked_at,
                reason=f"snapshot {path.stem}" + (f" (live failed: {reason})" if reason else ""),
                records=filtered,
            )
        except Exception as e:
            return self._result("unavailable", mode="fallback", reason=f"snapshot read failed: {e}")


def load_holidays_for_country(country: str, years: tuple[int, ...] = (2026, 2027)) -> list[dict[str, Any]]:
    """Load and merge holidays for a country across given years."""
    all_recs: list[dict[str, Any]] = []
    for y in years:
        loader = HolidaysLoader(country=country, year=y)
        res = loader.load()
        if res.records:
            all_recs.extend(res.records)
    all_recs.sort(key=lambda r: r["date"])
    return all_recs
