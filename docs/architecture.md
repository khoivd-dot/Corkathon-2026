# How the app works

> Describes the code on `main` as of 7 Nov 2026, 11:45. Update it in the same PR whenever the design changes.

## The idea in one line

A small Irish importer enters one shipment route, their invoice currency and how long their stock lasts, and gets a plain-English answer to **"Will my imports be late or dearer this month?"**, with one next step and every source dated.

## Big picture

```
 User form (web/)          inputs.py                    Live sources (sources/)
 ───────────────           ─────────                    ───────────────────────
 business, ports,  ──────▶ parse_inputs()               ECB rates   (ecb_fx)
 currency, fixed            validated, in memory        GDELT news  (gdelt)
 share, stock days,         only, never logged          CSO imports (cso_trade)   context
 lead time, dates                │                      Eurostat    (comext)      context
                                 │                            │
                                 │          cache → live → stale cache → snapshot
                                 ▼                            ▼
              ┌──────────────────────────┐   ┌──────────────────────────────┐
              │ events.py                │   │ exposure.py                  │
              │ news that names a port   │   │ stock buffer = stock − lead  │
              │ on YOUR route, in window │   │ FX change on unfixed share   │
              │ → reported / confirmed   │   │ (separate answer)            │
              └────────────┬─────────────┘   └──────────────┬───────────────┘
                           └──────────────┬─────────────────┘
                                          ▼
                     decision.py: alert / covered / insufficient,
                     headline, one next step, dated sources
                                          │
                     server.py  POST /api/answer  (nothing logged)
                                          ▼
                     web/ answer card: headline, delay card, cost card,
                     ports-we-can't-check line, "Show working" table
```

## Modules

| File | What it does |
|---|---|
| `src/corkathon/inputs.py` | Validates the form (`parse_inputs`) into `ImporterInputs`. Reports every error at once with plain wording. **In memory only**: never written to disk, cache or logs; `repr` is redacted. |
| `src/corkathon/sources/base.py` | Shared loader base (PR A): result shape, cache, live fetch, fallback. |
| `src/corkathon/sources/ecb_fx.py` | ECB daily reference rates for USD, GBP, CNY, JPY, CHF per euro. |
| `src/corkathon/sources/gdelt.py` | News on port and shipping disruption, grouped into incidents. |
| `src/corkathon/sources/cso_trade.py`, `comext.py` | Irish import values; context only, not used for the answer. |
| `src/corkathon/events.py` | Keeps only news that names a place on the user's route inside the time window; labels each event `reported` or `confirmed`. |
| `src/corkathon/exposure.py` | Stock buffer and FX exposure, as two separate answers. |
| `src/corkathon/decision.py` | The decision engine: turns inputs + sources into the answer-card JSON (state, headline, findings, next step, sources, dates line). |
| `src/corkathon/server.py` | Standard-library web server: `/healthz`, `POST /api/answer`, static files from `web/`, background GDELT refresh per port. |
| `web/` | Form and answer card. Calls `/api/answer`; falls back to `web/examples/*.json` if the API isn't available. |
| `docs/design/` | Mockups: alert, insufficient-evidence and error states; phone and desktop; light and dark. |
| `render.yaml` | Render deployment config. Auto-deploy **off**: deploying needs Tran's explicit yes. |

## Design principles (enforced in code and tests)

- **Never guess the route.** Ports come only from the user. No ports → no events.
- **News is a signal, not proof.** An event is `confirmed` only when a carrier or port authority's own page (from the reviewed `CONFIRMING_DOMAINS` list) names an event type and a place on the route, in the window. A news story that links to such a page isn't enough.
- **Confirmation is switched off for now** (`CONFIRMATION_ENABLED=0`), because the advisory pages' reuse terms aren't recorded yet. So today every event is "reported", and the app never raises an alert on news alone.
- **Never say "No action needed".** When we can't tell, we say "We can't determine whether your shipment is affected", still show any stock shortfall, and name the ports we can't check, with links to their notices.
- **Cost and delay are separate.** Exchange rates never confirm or imply a delay.
- **No made-up defaults.** If the user fixed "some" of the rate but didn't say how much, we don't assume 50%; we ask.
- **Nothing the user types is stored.** The cache holds source data only.
- **Every figure says where it came from and how fresh it is.**

## Inputs (`inputs.py`)

| Field | Question shown | Rules |
|---|---|---|
| `importer` | Business name | Required, ≤ 120 chars |
| `origin_port` | Port your goods leave from | Required |
| `transshipment_ports` | Ports your goods change ship at, if any | Comma-separated, max 5 |
| `destination_port` | Port your goods arrive at | Required |
| `currency` | Invoice currency | EUR, USD, GBP, CNY, JPY or CHF |
| `fixed_rate_share` | How much of this invoice have you already fixed an exchange rate for? | none / some / all |
| `fixed_rate_pct` | Roughly what share have you fixed? | 1–99%, only for "some"; may be blank |
| `stock_days` | How many days will your current stock last? | 0–3650 |
| `lead_time_days` | How many days from placing an order until it arrives? | 1–3650 |
| `window_start`, `window_end` | Dates your next shipment is expected to travel | End ≥ start |

## Events (`events.py`)

1. `Lane` holds the user's route: origin, transshipment ports, optional chokepoints (e.g. "Suez", only if the user confirms) and destination.
2. `lane_query(lane)` builds a tighter GDELT search: disruption terms **and** a place on the lane.
3. `filter_events(records, lane, start, end)`:
   - drops incidents outside the window or not naming a lane place (whole-word match);
   - merges near-duplicate incidents across queries (title similarity, within a day);
   - marks each as `reported` or `confirmed` (rules above), keeping the confirming URL.
4. `default_window(today, …)` looks back 14 days for news.

## Exposure (`exposure.py`)

**Stock:** `buffer = stock_days − lead_time_days`. Negative means a shortfall: *"Your stock runs out 14 days before a new order would arrive."* The arithmetic is kept so the screen can show its working.

**FX:** compares the ECB rate now with ~30 days earlier, applied only to the unfixed share of the invoice. Outcomes:

| Status | When |
|---|---|
| `computed` | Foreign-currency invoice with a known unfixed share; gives % change in euro cost |
| `not_applicable` | Invoice in euro, or rate fixed for all of it |
| `needs_share` | "Some" fixed but no % given: we ask instead of guessing |
| `unavailable` | No ECB rate loaded for that currency |

## Decision (`decision.py`)

`decide(inputs, sources, gdelt_records)` returns the answer-card JSON. The route text becomes a `Lane` via `inputs.to_lane`.

| State | When | Headline |
|---|---|---|
| `alert` | Confirmed event on the route **and** stock shortfall | "Check your forwarder's ETA today: your stock runs out N days before a new order would arrive." |
| `covered` | Confirmed event, stock covers lead time | "A confirmed event may affect your route. Your stock covers your lead time by N days." |
| `insufficient` | No confirmed event (always, while confirmation is off) | "We can't determine whether your shipment is affected." Next step still mentions any stock shortfall. |

Every answer also includes:
- the **FX card** (separate from delay; "not your bank's rate");
- a **coverage line**: "We can't confirm events at Rotterdam, Antwerp, Felixstowe, Dublin or Cork automatically. Check their notices directly.", with links to each port's notices page;
- a **dates line**, e.g. "Checked 11:05 UK time. Trade figures are August data, ECB rate as of 6 Nov, port news from 10:40.";
- a **sources table**: each source's period, published, checked, mode, how we used it and attribution. Carrier and port advisories are listed as "Not used yet: reuse terms not recorded".

## Server (`server.py`)

| Route | Does |
|---|---|
| `GET /healthz` | Returns `ok` (for Render's health check) |
| `POST /api/answer` | Form fields in, answer JSON out. Body max 8 KB; held in memory only, never logged |
| `GET /*` | Static files from `web/` |

A background thread refreshes GDELT news every `REFRESH_S` seconds (default 1800 = 30 min) for each port in `LANE_PORTS` (default Rotterdam, Antwerp, Felixstowe, Dublin, Cork). The cache is keyed by port, never by user. Listens on `PORT` (default 8000).

## Loader result and freshness (`sources/base.py`)

Every loader returns a `SourceResult`:

| Field | Meaning |
|---|---|
| `source_id`, `endpoint`, `licence` | What was called and how to attribute it |
| `status` | `ok`, `stale` (old cache used), `snapshot` (saved file used), `unavailable` |
| `mode` | `live` or `fallback` |
| `reference_period` | Period the data covers, e.g. `2026-08` |
| `published_at` | When the publisher released it (empty for ECB, GDELT) |
| `source_updated_at` | When the data itself last changed |
| `checked_at` | When we fetched it (`retrieved_at` is a deprecated alias) |
| `reason`, `records` | Why a fallback happened; the data rows |

**Load order:** `SNAPSHOT_ONLY=1` → snapshots only (tests/CI). Otherwise: fresh cache → live fetch (then cache it) → stale cache → newest dated snapshot → `unavailable`.

**Cache lifetimes** (`CACHE_DIR`, default `./.cache`): ECB 1 day, CSO and Comext 31 days, GDELT 30 minutes.

## Running it

Python 3.12, standard library only.

```bash
cp .env.example .env
make test                                      # 77 tests, offline
make snapshot                                  # fetch all sources live, save today's snapshots
PYTHONPATH=src python3 -m corkathon.server     # run the app at http://localhost:8000
```

Windows PowerShell commands are in [contributing.md](contributing.md).

Settings: `CONFIRMATION_ENABLED` (default off), `SNAPSHOT_ONLY` (legacy `SNAPSHOT`), `SNAPSHOT_DATE`, `CACHE_DIR`, `SOURCE_TIMEOUT_S` (default 20 s), `REFRESH_S` (default 1800), `LANE_PORTS`, `PORT` (default 8000), `LLM_ENABLED` / `LLM_API_KEY` (off by default).

## Deployment

`render.yaml` defines a Render Starter web service in Frankfurt with a 1 GB disk for the cache, `CONFIRMATION_ENABLED=0`, and auto-deploy off. **Nothing is deployed or made public without Tran's explicit yes.**

## Adding a data source

1. Create `src/corkathon/sources/<name>.py` inheriting `Loader`; set `source_id`, `endpoint`, `licence` and a `cache_ttl_s`; implement `fetch()` and `parse()` returning `(records, reference_period, published_at)`.
2. Register it in `registry.py`.
3. Save a real response to `tests/fixtures/` and add `tests/test_<name>.py`.
4. Add a row to `docs/sources.md` (licence checked, with date) and a section to `docs/data-sources-guide.md`.
5. `make snapshot`, commit the snapshot, open a small PR.

## Not built yet

- **Confirmation sources:** recording reuse terms for carrier and port advisories, so `CONFIRMATION_ENABLED` can be turned on.
- **When data counts as too old** per source for a user-facing warning.
- **Deployment:** configured, waiting on Tran's yes.
