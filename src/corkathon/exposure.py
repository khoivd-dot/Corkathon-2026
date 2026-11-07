"""Exposure calculation (PR D).

Stock buffer comes only from the user's inputs. FX exposure comes only from
the ECB reference rate on the share of the invoice without a fixed rate. The
two are separate answers: FX never confirms or implies a delay.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

# ECB series we load, keyed by invoice currency -> record field (foreign per EUR).
ECB_FIELDS = {c: f"{c.lower()}_per_eur" for c in ("USD", "GBP", "CNY", "JPY", "CHF")}


@dataclass(frozen=True)
class StockExposure:
    stock_days: int
    lead_time_days: int
    buffer_days: int  # stock_days - lead_time_days; negative = shortfall
    shortfall: bool
    arithmetic: str


@dataclass(frozen=True)
class FxExposure:
    currency: str
    status: str  # "computed" | "not_applicable" | "unavailable" | "needs_share"
    unfixed_share: float | None
    rate_from: float | None = None
    rate_to: float | None = None
    date_from: str | None = None
    date_to: str | None = None
    eur_cost_change_pct: float | None = None  # on the unfixed share of the invoice
    note: str = ""


def stock_exposure(stock_days: int, lead_time_days: int) -> StockExposure:
    b = stock_days - lead_time_days
    return StockExposure(stock_days, lead_time_days, b, b < 0,
                         f"Stock lasts {stock_days} days and a new order takes {lead_time_days} days, "
                         + (f"so you're {-b} days short." if b < 0 else f"so you have {b} days to spare."))


def stock_sentence(s: StockExposure) -> str:
    if s.shortfall:
        return f"Your stock runs out {-s.buffer_days} days before a new order would arrive."
    if s.buffer_days == 0:
        return "Your stock runs out on the day a new order would arrive."
    return f"Your stock covers your lead time by {s.buffer_days} days."


NEEDS_SHARE = "We need the share you've fixed to work out your euro cost."


def fx_exposure(currency: str, fixed_rate_share: float | None, ecb_records: list[dict],
                lookback_days: int = 30) -> FxExposure:
    if currency == "EUR":
        return FxExposure(currency, "not_applicable", None, note="Invoice is in euro, so there is no exchange-rate exposure.")
    if fixed_rate_share is None:  # "some" without a share: no amount, no default
        return FxExposure(currency, "needs_share", None, note=NEEDS_SHARE)
    unfixed = round(1.0 - fixed_rate_share, 4)
    if currency == "EUR":
        return FxExposure(currency, "not_applicable", unfixed, note="Invoice is in euro, so there is no exchange-rate exposure.")
    if unfixed == 0:
        return FxExposure(currency, "not_applicable", 0.0, note="You have fixed the rate for the whole invoice.")
    key = ECB_FIELDS.get(currency)
    rows = sorted((r for r in ecb_records if key and r.get(key) is not None),
                  key=lambda r: r["reference_period"])
    if not rows:
        return FxExposure(currency, "unavailable", unfixed, note=f"No ECB rate loaded for {currency}.")
    last = rows[-1]
    cutoff = (date.fromisoformat(last["reference_period"]) - timedelta(days=lookback_days)).isoformat()
    first = next((r for r in rows if r["reference_period"] >= cutoff), rows[0])
    a, b = float(first[key]), float(last[key])
    # Foreign currency per EUR: a lower rate means each foreign unit costs more euro.
    pct = round((a / b - 1.0) * 100.0 * unfixed, 2)
    return FxExposure(currency, "computed", unfixed, a, b, first["reference_period"], last["reference_period"], pct,
                      note=fx_sentence(first["reference_period"], last["reference_period"], pct))


def _d(iso: str) -> str:
    from datetime import date
    x = date.fromisoformat(iso)
    return f"{x.day} {x.strftime('%b')}"


def fx_sentence(start: str, end: str, pct: float) -> str:
    word = "higher" if pct >= 0 else "lower"
    return (f"Since {_d(start)}, the euro cost of the part you haven't fixed would be about "
            f"{abs(pct):.1f}% {word} (ECB rate as of {_d(end)}). This isn't your bank's rate. "
            "Ask for a current quote. Exchange rates say nothing about delays.")
