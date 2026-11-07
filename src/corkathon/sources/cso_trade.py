"""CSO merchandise imports by SITC commodity group (PxStat table TSM06).

Context only: monthly value of Irish imports (EUR thousand) for chosen
commodity groups. Each record carries its reference period, the table's
publication date and our retrieval date.
"""
from __future__ import annotations

import json
from typing import Any

from .base import Licence, Loader, http_json, now_iso, MONTH

MATRIX = "TSM06"
STAT_IMPORTS = "TSM06C1"
DIM_COMMODITY = "C02487V03011"
# 001008 = Coffee, tea, cocoa, spices (SITC 07); 001 = total food and live animals
DEFAULT_GROUPS = ("001008", "001")


class CsoTradeLoader(Loader):
    source_id = "cso_trade"
    endpoint = "https://ws.cso.ie/public/api.jsonrpc (PxStat.Data.Cube_API.ReadDataset, TSM06)"
    cache_ttl_s = MONTH
    licence = Licence(
        name="CC BY 4.0",
        url="https://www.cso.ie/en/aboutus/whoweare/copyrightpolicy/",
        attribution="Source: Central Statistics Office, Ireland (table TSM06), CC BY 4.0.",
    )

    def __init__(self, groups: tuple[str, ...] = DEFAULT_GROUPS, months: int = 13):
        self.groups = groups
        self.months = months

    def fetch(self) -> Any:
        body = {
            "jsonrpc": "2.0", "method": "PxStat.Data.Cube_API.ReadDataset",
            "params": {"class": "query", "id": ["STATISTIC", DIM_COMMODITY],
                       "dimension": {"STATISTIC": {"category": {"index": [STAT_IMPORTS]}},
                                     DIM_COMMODITY: {"category": {"index": list(self.groups)}}},
                       "extension": {"pivot": None, "codes": False, "language": {"code": "en"},
                                     "format": {"type": "JSON-stat", "version": "2.0"}, "matrix": MATRIX},
                       "version": "2.0"},
        }
        return http_json("https://ws.cso.ie/public/api.jsonrpc", json.dumps(body).encode())

    def parse(self, payload: Any):
        ds = payload["result"] if "result" in payload else payload
        dims, sizes, values = ds["id"], ds["size"], ds["value"]
        cats = [ds["dimension"][d]["category"] for d in dims]
        idx = [c["index"] if isinstance(c["index"], list) else sorted(c["index"], key=c["index"].get) for c in cats]
        t_pos = dims.index("TLIST(M1)")
        c_pos = dims.index(DIM_COMMODITY)
        published = ds.get("updated")
        unit = next(iter(cats[dims.index("STATISTIC")].get("unit", {}).values()), {}).get("label")
        retrieved = now_iso()
        records = []
        months = idx[t_pos][-self.months:]
        for flat, v in enumerate(values):
            if v is None:
                continue
            coord, rem = [], flat
            for s in reversed(sizes):
                coord.append(rem % s); rem //= s
            coord.reverse()
            month = idx[t_pos][coord[t_pos]]
            if month not in months:
                continue
            code = idx[c_pos][coord[c_pos]]
            records.append({
                "reference_period": f"{month[:4]}-{month[4:]}",
                "commodity_code": code,
                "commodity": cats[c_pos]["label"][code],
                "imports_value": v, "unit": unit,
                "published_at": published, "retrieved_at": retrieved,
            })
        if not records:
            raise ValueError("no non-null observations")
        ref = max(r["reference_period"] for r in records)
        return records, ref, published
