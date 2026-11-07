"""User inputs (PR C): validated, in memory only.

Nothing here is written to disk, cached or logged. `ImporterInputs.__repr__`
redacts values so an accidental log line can't leak what the user typed.
The route is whatever the user confirms; it is never inferred.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

CURRENCIES = ("EUR", "USD", "GBP", "CNY", "JPY", "CHF")
# Plain-language questions shown on the form (Behavioural Evidence wording).
QUESTIONS = {
    "importer": "Business name",
    "origin_port": "Port your goods leave from",
    "transshipment_ports": "Ports your goods change ship at, if any",
    "destination_port": "Port your goods arrive at",
    "currency": "Invoice currency",
    "fixed_rate_share": "How much of this invoice have you already fixed an exchange rate for? (None, some, all)",
    "fixed_rate_pct": "Roughly what share have you fixed? (for example 50%)",
    "stock_days": "How many days will your current stock last?",
    "lead_time_days": "How many days from placing an order until it arrives?",
    "order_window": "Dates your next shipment is expected to travel",
}
FIXED_SHARE = {"none": 0.0, "some": None, "all": 1.0}  # "some" needs fixed_rate_pct


class InputError(ValueError):
    def __init__(self, errors: dict[str, str]):
        super().__init__("invalid inputs: " + ", ".join(sorted(errors)))
        self.errors = errors  # field -> message, for the error summary


@dataclass(frozen=True, repr=False)
class ImporterInputs:
    importer: str
    origin_port: str
    destination_port: str
    currency: str
    fixed_rate_share: float | None  # 0..1 fixed; None = "some" with no share given
    stock_days: int
    lead_time_days: int
    window_start: date
    window_end: date
    transshipment_ports: tuple[str, ...] = field(default=())

    def __repr__(self) -> str:
        return "ImporterInputs(<redacted>)"

    __str__ = __repr__


def _int(form, key, errors, lo=0, hi=3650):
    raw = str(form.get(key, "")).strip()
    try:
        v = int(raw)
    except ValueError:
        errors[key] = "Enter a whole number of days"
        return 0
    if not lo <= v <= hi:
        errors[key] = f"Enter a number between {lo} and {hi}"
    return v


def _date(form, key, errors):
    try:
        return date.fromisoformat(str(form.get(key, "")).strip())
    except ValueError:
        errors[key] = "Enter a date like 2026-11-20"
        return date.min


def parse_inputs(form: dict) -> ImporterInputs:
    """Validate a submitted form. Raises InputError with every problem at once."""
    errors: dict[str, str] = {}
    text = {k: str(form.get(k, "")).strip() for k in ("importer", "origin_port", "destination_port")}
    for k, v in text.items():
        if not v:
            errors[k] = f"Enter {QUESTIONS[k].lower()}"
        elif len(v) > 120:
            errors[k] = "Keep this under 120 characters"
    tranship = tuple(p.strip() for p in str(form.get("transshipment_ports", "")).split(",") if p.strip())[:5]
    cur = str(form.get("currency", "")).strip().upper()
    if cur not in CURRENCIES:
        errors["currency"] = "Choose the invoice currency"
    share_raw = str(form.get("fixed_rate_share", "")).strip().lower()
    if share_raw not in FIXED_SHARE:
        errors["fixed_rate_share"] = "Choose none, some or all"
    share = FIXED_SHARE.get(share_raw)
    if share_raw == "some":
        pct_raw = str(form.get("fixed_rate_pct", "")).strip().rstrip("%").strip()
        if pct_raw:
            try:
                pct = float(pct_raw)
                if not 0 < pct < 100:
                    raise ValueError
                share = round(pct / 100.0, 4)
            except ValueError:
                errors["fixed_rate_pct"] = "Enter a percentage between 1 and 99, or leave it blank"
    stock = _int(form, "stock_days", errors)
    lead = _int(form, "lead_time_days", errors, lo=1)
    ws, we = _date(form, "window_start", errors), _date(form, "window_end", errors)
    if "window_start" not in errors and "window_end" not in errors and we < ws:
        errors["window_end"] = "The end date must be on or after the start date"
    if errors:
        raise InputError(errors)
    return ImporterInputs(importer=text["importer"], origin_port=text["origin_port"],
                          destination_port=text["destination_port"], currency=cur,
                          fixed_rate_share=share, stock_days=stock,
                          lead_time_days=lead, window_start=ws, window_end=we,
                          transshipment_ports=tranship)


def to_lane(inp: ImporterInputs):
    from .events import Lane
    return Lane(origin_port=inp.origin_port, destination_port=inp.destination_port,
                transshipment_ports=inp.transshipment_ports)
