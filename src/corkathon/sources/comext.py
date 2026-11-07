"""Eurostat Comext DS-045409: Ireland monthly imports by HS product.

Context only. Default: HS 0901 (coffee) from extra-EU27 partners, value in EUR
and quantity in 100 kg. Records carry reference period, Eurostat's
dissemination date and our retrieval date.
"""
from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

from .base import Licence, Loader, http_json, now_iso, MONTH

BASE = "https://ec.europa.eu/eurostat/api/comext/dissemination/statistics/1.0/data/DS-045409"


class ComextLoader(Loader):
    source_id = "comext"
    cache_ttl_s = MONTH
    licence = Licence(
        name="Eurostat free re-use (Commission Decision 2011/833/EU; CC BY 4.0 per Eurostat copyright notice; statistical reuse incl. commercial display and snapshots permitted with acknowledgement, modifications identified, disclaimer applied — checked 2026-11-07)",
        url="https://ec.europa.eu/eurostat/web/main/help/copyright-notice",
        attribution="Source: Eurostat (Comext DS-045409). Modifications, if any, must be stated.",
    )

    def __init__(self, product: str = "0901", partner: str = "EXT_EU27_2020", since: str = "2025-06"):
        q = [("reporter", "IE"), ("partner", partner), ("product", product), ("flow", "1"),
             ("indicators", "VALUE_IN_EUROS"), ("indicators", "QUANTITY_IN_100KG"),
             ("freq", "M"), ("sinceTimePeriod", since)]
        self.endpoint = f"{BASE}?{urlencode(q)}"

    def fetch(self) -> Any:
        return http_json(self.endpoint)

    def parse(self, ds: Any):
        dims, sizes, values = ds["id"], ds["size"], ds["value"]
        cats = {d: ds["dimension"][d]["category"] for d in dims}
        order = {d: sorted(cats[d]["index"], key=cats[d]["index"].get) for d in dims}
        published = ds.get("updated")
        retrieved = now_iso()
        rows: dict[tuple, dict] = {}
        for k, v in values.items():
            flat, coord = int(k), {}
            for d, s in zip(reversed(dims), reversed(sizes)):
                coord[d] = order[d][flat % s]; flat //= s
            key = (coord["time"], coord["product"], coord["partner"])
            row = rows.setdefault(key, {
                "reference_period": coord["time"], "product_code": coord["product"],
                "product": cats["product"]["label"][coord["product"]],
                "partner": cats["partner"]["label"][coord["partner"]],
                "published_at": published, "retrieved_at": retrieved})
            row[{"VALUE_IN_EUROS": "value_eur", "QUANTITY_IN_100KG": "quantity_100kg"}.get(coord["indicators"], coord["indicators"])] = v
        records = sorted(rows.values(), key=lambda r: r["reference_period"])
        if not records:
            raise ValueError("no observations (period not yet published?)")
        return records, records[-1]["reference_period"], published
