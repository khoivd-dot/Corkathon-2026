"""Met Éireann weather warnings for Irish destination ports.

Licence:
Met Éireann custom open data licence (CC BY 4.0 plus the verbatim and expiry conditions),
dataset listed on data.gov.ie (https://data.gov.ie/en_GB/dataset/weather-warnings).
Show headline, level, onset, expiry, issued verbatim. Never reword a warning or present
it as a different level. Drop warnings whose expiry has passed, including ones read
from a snapshot. Credit 'Met Éireann' next to every warning.
"""
from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from typing import Any

from .base import Licence, Loader, SourceResult, http_json, now_iso

# County/region codes for Irish ports in ports.py
# Cork / Ringaskiddy: EI04 (County Cork)
# Dublin: EI07 (County Dublin)
# Additional Irish ports (for future reference):
# Wexford/Rosslare: EI30
# Limerick/Foynes: EI16
# Waterford: EI27
PORT_REGIONS: dict[str, str] = {
    "cork": "EI04",
    "ringaskiddy": "EI04",
    "dublin": "EI07",
}


def strip_html(text: str) -> str:
    """Strip HTML tags and unescape entities, fixing whitespace only without changing wording."""
    if not text:
        return ""
    # Replace block/list tags with spaces so words don't run together
    s = re.sub(r"</?(?:p|ul|ol|li|div|br|h\d)[^>]*>", " ", text, flags=re.IGNORECASE)
    # Strip any remaining tags
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    # Normalize whitespace
    return " ".join(s.split())


def _parse_iso(iso_str: str | None) -> datetime | None:
    if not iso_str:
        return None
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def is_expired(expiry_str: str | None, now: datetime | None = None) -> bool:
    """Return True if expiry date/time has passed."""
    exp_dt = _parse_iso(expiry_str)
    if exp_dt is None:
        return False
    now = now or datetime.now(timezone.utc)
    return exp_dt <= now


def warnings_for_port(records: list[dict[str, Any]], port_name: str, now: datetime | None = None) -> list[dict[str, Any]]:
    """Return active (non-expired) warnings applicable to the given port."""
    if not port_name:
        return []
    clean_name = re.sub(r"\s*\(.*\)\s*$", "", port_name).strip().lower()
    region_code = PORT_REGIONS.get(clean_name)
    if not region_code:
        return []

    now = now or datetime.now(timezone.utc)
    matched = []
    for r in records:
        if is_expired(r.get("expiry"), now):
            continue
        regions = r.get("regions") or []
        if region_code in regions:
            matched.append(r)
    return matched


class MetWarningsLoader(Loader):
    source_id = "met_warnings"
    endpoint = "https://www.met.ie/Open_Data/json/warning_IRELAND.json"
    cache_ttl_s = 900  # 15 minutes
    licence = Licence(
        name="Met Éireann open data licence (CC BY 4.0, verbatim, expiry-filtered)",
        url="https://www.met.ie/Open_Data/Licence.txt",
        attribution="Source: Met Éireann (data.gov.ie)",
    )

    def fetch(self) -> Any:
        return http_json(self.endpoint)

    def parse(self, payload: Any, now: datetime | None = None):
        if not isinstance(payload, list):
            raise ValueError(f"expected list of warnings, got {type(payload).__name__}")

        now = now or datetime.now(timezone.utc)
        records: list[dict[str, Any]] = []
        latest_updated: str | None = None

        for item in payload:
            if not isinstance(item, dict):
                continue

            expiry = str(item.get("expiry") or "")
            # Drop warnings whose expiry has passed
            if is_expired(expiry, now):
                continue

            cap_id = str(item.get("capId") or item.get("id") or "")
            level = str(item.get("level") or "").lower()
            warning_type = str(item.get("type") or "")
            headline = str(item.get("headline") or "")
            issued = str(item.get("issued") or "")
            onset = str(item.get("onset") or "")
            regions = [str(reg) for reg in (item.get("regions") or [])]
            desc_text = strip_html(str(item.get("description") or ""))

            updated = str(item.get("updated") or issued)
            if updated and (latest_updated is None or updated > latest_updated):
                latest_updated = updated

            records.append({
                "id": cap_id,
                "level": level,
                "type": warning_type,
                "headline": headline,
                "issued": issued,
                "onset": onset,
                "expiry": expiry,
                "regions": regions,
                "description_text": desc_text,
            })

        ref_period = latest_updated[:10] if latest_updated else now_iso()[:10]
        return records, ref_period, latest_updated

    def load_snapshot(self, reason: str | None = None) -> SourceResult:
        res = super().load_snapshot(reason=reason)
        # Drop warnings whose expiry has passed, including ones read from a snapshot
        now = datetime.now(timezone.utc)
        if res.records:
            res.records = [r for r in res.records if not is_expired(r.get("expiry"), now)]
        return res
