# Data sources guide

Plain-English notes on each source: what it measures, how fresh it is, how the app uses it, and the catches. Licence details live in [`sources.md`](sources.md); keep both in step.

Figures are from the snapshots saved on 7 Nov 2026.

## At a glance

| Source | What it tells us | Freshness | Cached for | Used for |
|---|---|---|---|---|
| ECB reference rates | USD, GBP, CNY, JPY, CHF per euro | Every working day (~1 day old) | 1 day | **Cost answer** |
| GDELT | News on port strikes, closures, congestion, diversions | Minutes to hours | 30 min | **Delay answer** (signal) |
| Carrier / port pages | Official advisories, via GDELT links | As published | 30 min | Would turn a report into **confirmed**; off until reuse terms are recorded |
| CSO TSM06 | Irish imports by product group | Monthly, ~2–3 months behind | 31 days | Context only |
| Eurostat Comext | Irish coffee imports, value and weight | Monthly, ~2–3 months behind | 31 days | Context only |
| User inputs | Route, currency, stock, lead time | Typed now | Never stored | Everything |

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

## Considered and not used

| Source | Why not |
|---|---|
| AIS ship-tracking / port calls | Display rights unverified (shown as "unavailable" on the card) |
| CRO company register | Sector code 5630 mixes pubs with cafés, and sole traders aren't registered companies; not reliable for counting importers |

## Impact figures for the pitch

- **~49,600 Irish businesses imported goods in 2022; 98% were small or medium** (CSO, *Ireland's Trade in Goods 2022*, trade by enterprise size: 36,365 micro, 9,768 small, 2,692 medium, 780 large).
- **~3,500 cafés in Ireland, ~150 in Cork city** (poidata.io business listings, Dec 2025 / Jan 2026; not official). Useful only for the coffee example.

## What every answer must show

Each figure carries source, period and when we checked, e.g.:

> EUR/USD moved from 1.1378 to 1.1165 (ECB reference rate, 28 Sep – 6 Nov 2026; checked 7 Nov 2026, 11:27). This is not your bank's rate.

If a source fell back (`mode=fallback`), say "saved copy from <date>", not "live".
