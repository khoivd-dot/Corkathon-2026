# Data sources guide

Plain-English notes on each source: what it measures, how fresh it is, how the app uses it, and the catches. Licence details live in [`sources.md`](sources.md); keep both in step.

Figures are from the snapshots saved on 7 Nov 2026.

## At a glance

| Source | What it tells us | Freshness | Cached for | Used for |
|---|---|---|---|---|
| **Met Éireann warnings** | Official weather warnings (Yellow, Orange, Red) for Irish destination ports | Updated every few hours | 15 min | **Official route notices** (High Value Dataset on data.gov.ie) |
| **Nager.Date public holidays** | Public holidays at origin, transshipment, and Irish ports | Updated annually | 7 days | **Order-by timing calculation** |
| ECB reference rates | USD, GBP, CNY, JPY, CHF per euro | Every working day (~1 day old) | 1 day | **Cost answer** |
| GDELT | News on port strikes, closures, congestion, diversions | Minutes to hours | 30 min | **Delay answer** (signal) |
| Carrier / port pages | Official advisories, via GDELT links | As published | 30 min | Would turn a report into **confirmed**; off until reuse terms are recorded |
| CSO TSM06 | Irish imports by product group | Monthly, ~2–3 months behind | 31 days | Context only |
| Eurostat Comext | Irish coffee imports, value and weight | Monthly, ~2–3 months behind | 31 days | Context only |
| User inputs | Route, currency, stock, lead time | Typed now | Never stored | Everything |

## Met Éireann weather warnings (`met_warnings`)

- **What:** Official weather warnings published by Ireland's National Meteorological Service, listed on data.gov.ie as an EU High Value Dataset. JSON feed: `https://www.met.ie/Open_Data/json/warning_IRELAND.json`.
- **How it's used:** Maps destination ports to Irish counties (Cork and Ringaskiddy `EI04`, Dublin `EI07`). When an active warning covers the destination port, it is rendered as an "Official notice on your route".
- **Licence & rules:** Met Éireann custom open data licence (CC BY 4.0):
  - Must display `headline`, `level`, `onset`, `expiry`, and `issued` **verbatim**.
  - Never reword a warning or present it as a different severity.
  - Automatically drop warnings whose `expiry` timestamp has passed (even when loaded from a snapshot).
  - Credit "Met Éireann (data.gov.ie)".

## Nager.Date public holidays (`holidays`)

- **What:** Worldwide public holidays API (`https://date.nager.at/api/v3/PublicHolidays/{year}/{CC}`). Country codes are extracted from the first two characters of each port's UN/LOCODE in `ports.py` (e.g., `CNSHA` → `CN`, `IEDUB` → `IE`).
- **How it's used:** `corkathon.timing.compute_timing` uses holidays at origin (dispatch delays), destination (clearance/arrival delays), and Chinese New Year dates to calculate the latest viable order date before stock depletion.
- **Licence:** MIT licence. Cached per country and year for 7 days. Only `global: true` national holidays are kept.

## ECB reference rates (`ecb_fx`)

- **What:** official daily rates, last 30 working days, for the five non-euro invoice currencies the form offers. 28 Sep → 6 Nov 2026: USD 1.1378 → 1.1165, GBP 0.858 → 0.834, CNY 7.64 → 7.45, JPY 178.5 → 176.8, CHF 0.946 → 0.914 (all per euro, so every one got dearer for euro buyers).
- **How it's used:** `exposure.fx_exposure` compares today's rate with ~30 days earlier and applies the change to the **unfixed** share of the invoice.
- **Catches:**
  - It's the ECB rate, **not the user's bank rate**. The answer card says so.
  - No exact release time in the API, so `published_at` is empty; ECB publishes around 16:00 CET each working day. No weekend or holiday rates.
  - Says nothing about delays.
- **Licence:** ESCB reuse policy. Don't alter the statistics; quote "Source: ECB statistics." Label our % changes as our calculation.

## GDELT news (`gdelt`)

- **What:** global news search. The loader asks about port strikes, shipping disruption, Red Sea shipping and port congestion over 14 days; `events.lane_query` makes a tighter query with the user's own ports.
- **How it's used:** `events.filter_events` keeps only incidents naming a place on the user's route inside the window, merges duplicates, and labels them:
  - **reported**: news only. Never treated as confirmation.
  - **confirmed**: an advisory on a carrier or port authority domain (Maersk, MSC, CMA CGM, Hapag-Lloyd, ONE, Evergreen, COSCO, Yang Ming, ZIM; ports of Cork, Dublin, Rotterdam, Antwerp-Bruges, Hamburg, Singapore; Suez Canal Authority) that names an event type and a place on the route.
- **Right now:** confirmation is switched off (`CONFIRMATION_ENABLED=0`) until the advisory pages' reuse terms are recorded, so every event shows as "reported" and the app abstains rather than alerting. Instead it links to each port's official notices page (Rotterdam, Antwerp, Felixstowe, Dublin, Cork) so the user can check.
- **Refresh:** the server re-fetches news for each of those ports every 30 minutes.
- **Catches:**
  - Keyword matching: irrelevant stories can match a port name.
  - Only as good as news coverage; a quiet delay may never be reported.
  - We never know whether the user's own shipment is affected. The card says "We can't tell yet whether your shipment is affected."
  - Max 1 request every 5 s (loader waits 6 s).
- **Licence:** free with citation/link; snapshots and redistribution allowed; does **not** license the publishers' full articles, so show headlines and links, not article text.

## CSO TSM06 (`cso_trade`): context

- **What:** monthly value of Irish imports (€ thousand) for "coffee, tea, cocoa, spices" and "total food and live animals". Latest: August 2026, published 16 Oct 2026.
- **Use:** background in "Show working", not the answer.
- **Catches:** broad groups; value only; 2–3 months behind.
- **Licence:** CC BY 4.0. "Source: Central Statistics Office, Ireland (table TSM06)."

## Eurostat Comext (`comext`): context

- **What:** Ireland's monthly coffee imports (HS 0901) from outside the EU, in € and 100 kg. Average about €9.20/kg in August 2026.
- **Use:** context for the coffee example.
- **Catches:** national average across all grades and origins; goods routed via another EU country aren't counted; recent months get revised.
- **Licence:** Eurostat free reuse (checked 7 Nov 2026): commercial display and snapshots allowed with acknowledgement; identify any modifications and apply Eurostat's disclaimer.
