"""ECB euro foreign exchange reference rate, USD per EUR (EXR D.USD.EUR.SP00.A).

Returns the rate series only. No interpretation or advice wording here.
"""
from __future__ import annotations

from typing import Any

from .base import Licence, Loader, http_json, now_iso

SERIES = "EXR/D.USD.EUR.SP00.A"


class EcbFxLoader(Loader):
    source_id = "ecb_fx"
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
        dims = payload["structure"]["dimensions"]["observation"][0]["values"]
        series = next(iter(payload["dataSets"][0]["series"].values()))
        # The API exposes only the response "prepared" time, not a release time, so
        # published_at stays None (ECB publishes reference rates ~16:00 CET each TARGET day).
        published = None
        retrieved = now_iso()
        records = []
        for i, obs in sorted(series["observations"].items(), key=lambda kv: int(kv[0])):
            if obs[0] is None:
                continue
            records.append({"reference_period": dims[int(i)]["id"], "usd_per_eur": obs[0],
                            "published_at": published, "retrieved_at": retrieved})
        if not records:
            raise ValueError("no observations")
        return records, records[-1]["reference_period"], published
