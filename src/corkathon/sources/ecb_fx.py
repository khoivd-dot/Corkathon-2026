"""ECB euro foreign exchange reference rates per EUR for USD, GBP, CNY, JPY, CHF
(EXR D.<CUR>.EUR.SP00.A), fetched in one request and merged by date.

Returns the rate series only. No interpretation or advice wording here.
"""
from __future__ import annotations

from typing import Any

from .base import Licence, Loader, http_json, now_iso, DAY

MAIN = ("USD", "GBP", "CNY", "JPY", "CHF")
# More ECB reference currencies (live fetch; the 7 Nov snapshot holds MAIN only).
EXTRA = ("SEK", "DKK", "NOK", "PLN", "CZK", "HUF", "RON", "CAD", "AUD", "NZD", "INR", "KRW", "SGD", "HKD", "THB", "TRY", "BRL", "MXN", "ZAR")
CURRENCIES = MAIN + EXTRA
SERIES = "EXR/D." + "+".join(CURRENCIES) + ".EUR.SP00.A"


class EcbFxLoader(Loader):
    source_id = "ecb_fx"
    cache_ttl_s = DAY
    licence = Licence(
        name="ESCB statistics free reuse policy (unmodified, source quoted)",
        url="https://www.ecb.europa.eu/stats/ecb_statistics/governance_and_quality_framework/html/usage_policy.en.html",
        attribution="Source: ECB statistics.",
    )

    def __init__(self, last_n: int = 30):
        self.endpoint = f"https://data-api.ecb.europa.eu/service/data/{SERIES}?lastNObservations={last_n}&format=jsondata"

    def fetch(self) -> Any:
        return http_json(self.endpoint)

    def parse(self, payload: Any):
        obs_dims = payload["structure"]["dimensions"]["observation"][0]["values"]
        sdims = payload["structure"]["dimensions"]["series"]
        cur_pos = next(i for i, d in enumerate(sdims) if d["id"] == "CURRENCY")
        cur_vals = [v["id"] for v in sdims[cur_pos]["values"]]
        # The API exposes only the response "prepared" time, not a release time, so
        # published_at stays None (ECB publishes reference rates ~16:00 CET each TARGET day).
        published = None
        retrieved = now_iso()
        by_date: dict[str, dict] = {}
        for key, series in payload["dataSets"][0]["series"].items():
            cur = cur_vals[int(key.split(":")[cur_pos])]
            for i, obs in series["observations"].items():
                if obs[0] is None:
                    continue
                d = obs_dims[int(i)]["id"]
                rec = by_date.setdefault(d, {"reference_period": d, "published_at": published, "retrieved_at": retrieved})
                rec[f"{cur.lower()}_per_eur"] = obs[0]
        records = [by_date[d] for d in sorted(by_date)]
        if not records:
            raise ValueError("no observations")
        return records, records[-1]["reference_period"], published
