"""Timing calculation engine for In Time order-by dates.

Pure functions, no I/O. Computes the latest date to place the next order
taking into account stock days, lead time, public holidays at origin/destination,
and Chinese New Year slowdown rules.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

CNY_SLOWDOWN_DAYS = 14
DISPATCH_WINDOW_DAYS = 7
DEST_ARRIVAL_WINDOW_DAYS = 3
MAX_SEARCH_STEPS = 500

CNY_ASSUMPTION = "Chinese New Year adds 14 days when it falls between ordering and arrival (rule of thumb, not data)."


def _to_date(d: str | date | datetime) -> date:
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, date):
        return d
    return date.fromisoformat(str(d)[:10])


def _format_headline_date(d: date) -> str:
    """Format date like 'Sun 3 Jan.' or 'Sat 5 Dec.'"""
    day_name = d.strftime("%a")
    month_name = d.strftime("%b")
    return f"{day_name} {d.day} {month_name}."


def compute_delays_for_date(
    d: date,
    lead_days: int,
    origin_country: str,
    dest_country: str,
    holidays: list[dict[str, Any]],
    origin_port: str = "",
    dest_port: str = "",
) -> list[dict[str, Any]]:
    """Compute delay entries for an order placed on date d.

    - 1 day for each weekday holiday in origin_country within [d, d+7] (dispatch window)
    - 1 day for each weekday holiday in dest_country within [arrival-3, arrival] (arrival window)
    - CNY_SLOWDOWN_DAYS (14) if origin is CN/HK and CNY falls in [d, d+lead_days]
    """
    origin_cc = origin_country.upper() if origin_country else ""
    dest_cc = dest_country.upper() if dest_country else ""
    base_arrival = d + timedelta(days=lead_days)
    delays: list[dict[str, Any]] = []

    # 1. Chinese New Year check
    if origin_cc in ("CN", "HK"):
        for h in holidays:
            h_cc = str(h.get("country", "")).upper()
            if h_cc in ("CN", "HK"):
                h_name = str(h.get("name", ""))
                if "Chinese New Year" in h_name or "Spring Festival" in h_name:
                    h_date = _to_date(h["date"])
                    if d <= h_date <= base_arrival:
                        place_name = origin_port or ("Shanghai" if origin_cc == "CN" else "Hong Kong")
                        delays.append({
                            "kind": "rule",
                            "place": place_name,
                            "country": origin_cc,
                            "date_from": h_date.isoformat(),
                            "date_to": (h_date + timedelta(days=CNY_SLOWDOWN_DAYS)).isoformat(),
                            "days_added": CNY_SLOWDOWN_DAYS,
                            "label": "Chinese New Year slowdown (rule of thumb)",
                            "source": "Nager.Date date, In Time rule",
                            "rule": True,
                            "_holiday_name": h_name,
                            "_holiday_date": h_date,
                        })
                        break

    # 2. Origin dispatch holidays: weekday holidays in [d, d+7]
    dispatch_end = d + timedelta(days=DISPATCH_WINDOW_DAYS)
    for h in holidays:
        if str(h.get("country", "")).upper() == origin_cc:
            h_date = _to_date(h["date"])
            # Weekdays only (weekday < 5)
            if d <= h_date <= dispatch_end and h_date.weekday() < 5:
                delays.append({
                    "kind": "holiday",
                    "place": origin_port or origin_cc,
                    "country": origin_cc,
                    "date_from": h_date.isoformat(),
                    "date_to": h_date.isoformat(),
                    "days_added": 1,
                    "label": f"{h.get('name', 'Public Holiday')} at origin port",
                    "source": "Nager.Date public holidays",
                    "rule": False,
                    "_holiday_name": h.get("name", ""),
                    "_holiday_date": h_date,
                })

    # 3. Destination arrival holidays: weekday holidays in [arrival-3, arrival]
    arr_window_start = base_arrival - timedelta(days=DEST_ARRIVAL_WINDOW_DAYS)
    for h in holidays:
        if str(h.get("country", "")).upper() == dest_cc:
            h_date = _to_date(h["date"])
            if arr_window_start <= h_date <= base_arrival and h_date.weekday() < 5:
                delays.append({
                    "kind": "holiday",
                    "place": dest_port or dest_cc,
                    "country": dest_cc,
                    "date_from": h_date.isoformat(),
                    "date_to": h_date.isoformat(),
                    "days_added": 1,
                    "label": f"{h.get('name', 'Public Holiday')} at destination port",
                    "source": "Nager.Date public holidays",
                    "rule": False,
                    "_holiday_name": h.get("name", ""),
                    "_holiday_date": h_date,
                })

    return delays


def effective_lead(
    d: date,
    lead_days: int,
    origin_country: str,
    dest_country: str,
    holidays: list[dict[str, Any]],
    origin_port: str = "",
    dest_port: str = "",
) -> int:
    """Return effective lead days for order placed on date d."""
    delays = compute_delays_for_date(
        d, lead_days, origin_country, dest_country, holidays, origin_port, dest_port
    )
    return lead_days + sum(delay["days_added"] for delay in delays)


def compute_timing(
    stock_days: int,
    lead_days: int,
    origin_country: str,
    dest_country: str,
    holidays: list[dict[str, Any]],
    notices: list[dict[str, Any]],
    as_of: str | date | datetime,
    origin_port: str = "",
    dest_port: str = "",
    sources: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Compute the timing block for In Time.

    Returns dict matching shared contract.
    """
    as_of_d = _to_date(as_of)
    stock_out = as_of_d + timedelta(days=stock_days)

    # Search backwards from stock_out for the latest date d in [as_of_d, stock_out]
    # where d + effective_lead(d) <= stock_out
    order_by_found: date | None = None
    step_limit = min(MAX_SEARCH_STEPS, (stock_out - as_of_d).days)

    if step_limit >= 0:
        curr = stock_out
        for _ in range(step_limit + 1):
            if curr < as_of_d:
                break
            eff = effective_lead(
                curr, lead_days, origin_country, dest_country, holidays, origin_port, dest_port
            )
            if curr + timedelta(days=eff) <= stock_out:
                order_by_found = curr
                break
            curr -= timedelta(days=1)

    # Arrival if ordered today
    eff_today = effective_lead(
        as_of_d, lead_days, origin_country, dest_country, holidays, origin_port, dest_port
    )
    arr_today = as_of_d + timedelta(days=eff_today)

    if order_by_found is not None:
        order_by = order_by_found
        days_left = (order_by - as_of_d).days
        status = "soon" if days_left <= 7 else "plan"
        headline = f"Order by {_format_headline_date(order_by)}"

        delays = compute_delays_for_date(
            order_by, lead_days, origin_country, dest_country, holidays, origin_port, dest_port
        )
        eff_order_by = lead_days + sum(delay["days_added"] for delay in delays)

        # Reason formulation
        cny_delay = next((delay for delay in delays if delay.get("rule")), None)
        if cny_delay:
            place = cny_delay["place"]
            dt_from = _to_date(cny_delay["date_from"])
            cny_str = f"{dt_from.day} {dt_from.strftime('%b')}"
            reason = f"After that, Chinese New Year at {place} ({cny_str}) pushes arrival past the day your stock runs out."
        elif delays:
            # Sort by days_added descending to get biggest delay
            biggest = max(delays, key=lambda d: d["days_added"])
            dt_from = _to_date(biggest["date_from"])
            date_str = f"{dt_from.day} {dt_from.strftime('%b')}"
            reason = f"After that, {biggest['label']} ({date_str}) pushes arrival past the day your stock runs out."
        else:
            reason = "No holidays on your route change this date."

    else:
        # Late: even ordered at as_of, arrival is after stock_out
        order_by = as_of_d
        days_left = 0
        status = "late"
        days_late = (arr_today - stock_out).days
        headline = "Order today."
        reason = f"Even ordered now, it arrives {days_late} day{'s' if days_late != 1 else ''} after your stock runs out."
        delays = compute_delays_for_date(
            as_of_d, lead_days, origin_country, dest_country, holidays, origin_port, dest_port
        )
        eff_order_by = eff_today

    # Clean up internal helper keys from delays
    clean_delays = []
    has_rule_delay = False
    for delay in delays:
        cd = {k: v for k, v in delay.items() if not k.startswith("_")}
        clean_delays.append(cd)
        if cd.get("rule"):
            has_rule_delay = True

    assumptions = [CNY_ASSUMPTION] if has_rule_delay else []

    if sources is None:
        sources = [{
            "name": "Nager.Date public holidays",
            "checked": datetime.now().astimezone().replace(microsecond=0).isoformat(),
            "mode": "live",
        }]

    return {
        "as_of": as_of_d.isoformat(),
        "order_by": order_by.isoformat(),
        "days_left": days_left,
        "status": status,
        "headline": headline,
        "reason": reason,
        "stock_out": stock_out.isoformat(),
        "arrival_if_ordered_today": arr_today.isoformat(),
        "base_lead_days": lead_days,
        "effective_lead_days": eff_order_by,
        "delays": clean_delays,
        "notices": notices,
        "assumptions": assumptions,
        "sources": sources,
    }
