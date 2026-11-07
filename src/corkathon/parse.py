"""Plain-English shipment query parser.

Uses regex only, no LLM. Maps natural language questions and descriptions into
form fields compatible with inputs.parse_inputs, and returns structured 'understood'
and 'missing' chips.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any

from .inputs import CURRENCIES, parse_inputs
from .ports import PORTS, lookup

# Word numbers up to 52
WORD_NUMS = {
    "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
    "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
}

# Sorted port keys by length descending to match longest first
PORT_KEYS_ORDERED = sorted(PORTS.keys(), key=lambda k: len(k), reverse=True)

CURRENCY_PATTERNS = [
    (r"\b(?:dollars?|usd|\$)\b", "USD"),
    (r"\b(?:sterling|pounds?|gbp|£)\b", "GBP"),
    (r"\b(?:yuan|rmb|cny)\b", "CNY"),
    (r"\b(?:yen|jpy|¥)\b", "JPY"),
    (r"\b(?:francs?|chf)\b", "CHF"),
    (r"\b(?:euros?|eur|€)\b", "EUR"),
]

NUM_WORDS = "a|an|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve"


def _parse_qty(qty_str: str) -> int | None:
    s = qty_str.lower().strip()
    if s.isdigit():
        return int(s)
    return WORD_NUMS.get(s)


def _unit_multiplier(unit_str: str) -> int:
    u = unit_str.lower()
    if "week" in u:
        return 7
    if "month" in u:
        return 30
    return 1


def _extract_ports(text: str) -> tuple[str | None, list[str], str | None]:
    """Extract origin, transshipment, and destination ports from text."""
    lower_text = text.lower()
    matches: list[tuple[int, int, str]] = []  # (start, end, port_name)

    for p in PORT_KEYS_ORDERED:
        pattern = r"\b" + re.escape(p.lower()) + r"\b"
        for m in re.finditer(pattern, lower_text):
            if not any(start <= m.start() < end or start < m.end() <= end for start, end, _ in matches):
                matches.append((m.start(), m.end(), p))

    matches.sort(key=lambda x: x[0])

    origin: str | None = None
    transshipment: list[str] = []
    dest: str | None = None
    assigned_indices = set()

    # Pass 1: preposition-based matching
    for i, (start, end, port) in enumerate(matches):
        prefix = lower_text[max(0, start - 20):start].strip()
        if re.search(r"\b(?:from|leaving|out of)\s*$", prefix):
            origin = port
            assigned_indices.add(i)
        elif re.search(r"\b(?:via|through)\s*$", prefix):
            transshipment.append(port)
            assigned_indices.add(i)
        elif re.search(r"\b(?:to|into|destined for)\s*$", prefix):
            dest = port
            assigned_indices.add(i)

    # Pass 2: fallback based on Irish vs non-Irish ports
    unassigned = [matches[i] for i in range(len(matches)) if i not in assigned_indices]
    for start, end, port in unassigned:
        hit = lookup(port)
        locode = hit[1] if hit else ""
        is_irish = locode.startswith("IE")

        if is_irish and dest is None:
            dest = port
        elif not is_irish and origin is None:
            origin = port
        elif origin is not None and dest is not None and port not in transshipment:
            transshipment.append(port)

    return origin, transshipment, dest


def _extract_durations(text: str) -> tuple[int | None, int | None]:
    """Extract stock_days and lead_time_days from text."""
    stock_days: int | None = None
    lead_days: int | None = None

    # Stock patterns:
    # 1. "X days/weeks of stock", "X weeks left", "X weeks remaining"
    m_stock1 = re.search(
        rf"\b(\d+|{NUM_WORDS})\s*(days?|weeks?|months?)\s*(?:of\s+)?(?:stock|left|remaining|lasts?|lasting|enough\s+for)\b",
        text,
        flags=re.IGNORECASE,
    )
    # 2. "stock of X weeks", "enough for X weeks"
    m_stock2 = re.search(
        rf"\b(?:stock\s+(?:of|is)|have|with|enough\s+for)\s*(?:about\s+)?(\d+|{NUM_WORDS})\s*(days?|weeks?|months?)\b",
        text,
        flags=re.IGNORECASE,
    )

    if m_stock1:
        qty = _parse_qty(m_stock1.group(1))
        if qty:
            stock_days = qty * _unit_multiplier(m_stock1.group(2))
    elif m_stock2:
        qty = _parse_qty(m_stock2.group(1))
        if qty:
            stock_days = qty * _unit_multiplier(m_stock2.group(2))

    # Lead time patterns:
    # 1. "takes X weeks to get here", "takes X weeks", "lead time is X weeks"
    m_lead1 = re.search(
        rf"\b(?:takes?|lead(?:\s+time)?\s+(?:is|of)?)\s*(?:about\s+)?(\d+|{NUM_WORDS})\s*(days?|weeks?|months?)(?:\s*(?:to\s+arrive|to\s+get\s+here|lead\s+time|shipping|to\s+ship))?\b",
        text,
        flags=re.IGNORECASE,
    )
    # 2. "X weeks to arrive", "X weeks to get here"
    m_lead2 = re.search(
        rf"\b(\d+|{NUM_WORDS})\s*(days?|weeks?|months?)\s*(?:to\s+arrive|to\s+get\s+here|lead\s+time|shipping|to\s+ship)\b",
        text,
        flags=re.IGNORECASE,
    )

    if m_lead1:
        qty = _parse_qty(m_lead1.group(1))
        if qty:
            lead_days = qty * _unit_multiplier(m_lead1.group(2))
    elif m_lead2:
        qty = _parse_qty(m_lead2.group(1))
        if qty:
            lead_days = qty * _unit_multiplier(m_lead2.group(2))

    return stock_days, lead_days


def _extract_currency(text: str) -> str | None:
    for pattern, code in CURRENCY_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return code
    return None


def _extract_fixed_share(text: str) -> tuple[str, str]:
    """Returns (fixed_rate_share, fixed_rate_pct) where share is 'none', 'some', or 'all'."""
    lower = text.lower()
    if re.search(r"\b(half fixed|50% fixed)\b", lower):
        return "some", "50"
    if re.search(r"\b(fixed the rate|rate is fixed|fully fixed|all fixed)\b", lower):
        return "all", ""
    if re.search(r"\b(not fixed|unfixed|no hedge|not hedged)\b", lower):
        return "none", ""

    pct_m = re.search(r"\b(\d{1,2})%\s*(?:fixed|hedged)\b", lower)
    if pct_m:
        return "some", pct_m.group(1)

    return "none", ""


def _extract_importer(text: str) -> str | None:
    """Extract business or goods name from query."""
    m = re.search(
        r"\b(?:i\s+bring|we\s+bring|importing|import|imports)\s+([a-zA-Z0-9\s\-]+?)\s+(?:from|to|into|via|through|in\b)",
        text,
        flags=re.IGNORECASE,
    )
    if m:
        item = m.group(1).strip()
        if item and len(item) <= 40:
            return item.capitalize()

    m2 = re.match(r"^\s*([a-zA-Z0-9\s\-]+?)\s+from\s+[A-Za-z]", text, flags=re.IGNORECASE)
    if m2:
        item = m2.group(1).strip()
        if item and not re.search(r"\b(?:will|can|is|are|how|when|what|my|our)\b", item, flags=re.IGNORECASE):
            if len(item) <= 40:
                return item.capitalize()

    return None


def parse_query(q: str, today: date | None = None) -> dict[str, Any]:
    """Parse a plain-English shipment query into form fields and understood/missing tags."""
    today = today or date.today()
    q_clean = (q or "").strip()

    origin, transshipment, dest = _extract_ports(q_clean)
    stock_days, lead_days = _extract_durations(q_clean)
    currency = _extract_currency(q_clean)
    share, pct = _extract_fixed_share(q_clean)
    importer = _extract_importer(q_clean)

    has_any_signal = bool(origin or dest or stock_days is not None or lead_days is not None or currency)

    fields: dict[str, Any] = {}
    understood: list[dict[str, str]] = []
    missing: list[str] = []

    if not has_any_signal:
        return {
            "fields": {},
            "understood": [],
            "missing": ["origin_port", "destination_port", "currency", "stock_days", "lead_time_days"],
        }

    # Importer
    if importer:
        fields["importer"] = importer
        understood.append({"field": "importer", "text": f"Business: {importer}"})
    else:
        fields["importer"] = "My business"

    # Ports
    if origin:
        fields["origin_port"] = origin
        understood.append({"field": "origin_port", "text": f"From {origin}"})
    else:
        missing.append("origin_port")

    if transshipment:
        fields["transshipment_ports"] = ", ".join(transshipment)
        understood.append({"field": "transshipment_ports", "text": f"Via {', '.join(transshipment)}"})
    else:
        fields["transshipment_ports"] = ""

    if dest:
        fields["destination_port"] = dest
        understood.append({"field": "destination_port", "text": f"To {dest}"})
    else:
        missing.append("destination_port")

    # Currency
    if currency:
        fields["currency"] = currency
        understood.append({"field": "currency", "text": f"Paid in {currency}"})
    else:
        missing.append("currency")

    # Fixed share
    fields["fixed_rate_share"] = share
    if share == "some" and pct:
        fields["fixed_rate_pct"] = pct
        understood.append({"field": "fixed_rate_pct", "text": f"{pct}% fixed"})
    elif share == "all":
        fields["fixed_rate_pct"] = ""
        understood.append({"field": "fixed_rate_share", "text": "Fully fixed rate"})
    elif "not fixed" in q_clean.lower() or "unfixed" in q_clean.lower():
        fields["fixed_rate_pct"] = ""
        understood.append({"field": "fixed_rate_share", "text": "Rate not fixed"})
    else:
        fields["fixed_rate_pct"] = ""

    # Durations
    if stock_days is not None:
        fields["stock_days"] = str(stock_days)
        understood.append({"field": "stock_days", "text": f"{stock_days} days of stock"})
    else:
        missing.append("stock_days")

    if lead_days is not None:
        fields["lead_time_days"] = str(lead_days)
        understood.append({"field": "lead_time_days", "text": f"{lead_days} days lead time"})
    else:
        missing.append("lead_time_days")

    # Default travel window
    w_start = today
    w_end = today + timedelta(days=21)
    fields["window_start"] = w_start.isoformat()
    fields["window_end"] = w_end.isoformat()

    return {
        "fields": fields,
        "understood": understood,
        "missing": missing,
    }
