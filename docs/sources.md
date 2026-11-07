# Data sources

| source_id | Endpoint | Licence | Attribution | Role |
|---|---|---|---|---|
| met_warnings | `https://www.met.ie/Open_Data/json/warning_IRELAND.json` | Met Éireann custom open data licence (CC BY 4.0, verbatim, expiry-filtered) — listed on data.gov.ie as EU High Value Dataset | Source: Met Éireann (data.gov.ie) | Official route notices for Irish ports |
| holidays | `https://date.nager.at/api/v3/PublicHolidays/{year}/{CC}` | Nager.Date public holidays (MIT) — https://date.nager.at | Source: Nager.Date | Public holidays at origin/destination for order-by engine |
| cso_trade | CSO PxStat TSM06 (imports by SITC group, monthly, EUR thousand) | CC BY 4.0 — https://www.cso.ie/en/aboutus/whoweare/copyrightpolicy/ | Source: Central Statistics Office, Ireland | Context only |
| ecb_fx | ECB Data Portal EXR D.<CUR>.EUR.SP00.A (daily reference rate) for USD, GBP, CNY, JPY, CHF plus 19 more ECB currencies (the 7 Nov snapshot holds the first five) | ESCB free reuse policy — https://www.ecb.europa.eu/stats/ecb_statistics/governance_and_quality_framework/html/usage_policy.en.html (must not modify statistics) | Source: ECB statistics. | Rate series only |
| comext | Eurostat Comext DS-045409, reporter IE, HS 0901, extra-EU27, monthly value EUR + 100 kg | Eurostat free re-use, Decision 2011/833/EU / CC BY 4.0 — https://ec.europa.eu/eurostat/web/main/help/copyright-notice ; statistical reuse incl. commercial display and snapshots permitted with acknowledgement; identify modifications and apply Eurostat's disclaimer (checked 2026-11-07) | Source: Eurostat | Context only |
| gdelt (official) | Same GDELT API, query limited to `domain:` official carrier and port sites (CONFIRMING_DOMAINS in events.py). Only when `CONFIRMATION_ENABLED=1` | As gdelt. We show the headline and a link to the official page, never the page's text. Each carrier's and port's own site terms still apply to the page itself: **to confirm before public display** | Source: The GDELT Project; the linked carrier or port page | Confirmation: an official page naming a disruption and a port on the route |
| ais | AISHub `ws.php` JSON, a 0.25° box around each known port, one request a minute. Only when `AIS_ENABLED=1` and `AISHUB_USERNAME` is set | AISHub data sharing: API access for members who contribute an AIS receiver feed, non-commercial — https://www.aishub.net/join-us . We keep and show **aggregate counts only** (at anchor, moored, moving), never ship names, positions or tracks. **Terms to confirm before public display** | Ship counts: AISHub | Context only |
| aisstream | aisstream.io websocket `wss://stream.aisstream.io/v0/stream`, one short connection per lookup filtered to a single MMSI, waits up to `AIS_LIVE_WAIT_S` (25 s) for the next position report, cached 5 min per MMSI. Only when `AIS_LIVE_ENABLED=1` and `AISSTREAM_API_KEY` is set | aisstream.io free API (beta, no SLA, throttled per key and user); key from signing in with GitHub at https://aisstream.io . Docs ask that the key stays server-side, which we do. Written display/redistribution terms not found on 2026-11-07 (site not reachable from our build box): **terms to confirm before public display**, so the flag stays off on Render. Terrestrial receivers only, so ships in open ocean often have no position. Only the ship the user asked for is looked up; MMSIs of commercial ships are public identifiers, not personal data | Ship position: aisstream.io (terrestrial AIS) | Context only |
| (page links) | Carrier tracking pages (Maersk, MSC, CMA CGM, Hapag-Lloyd, ONE, Evergreen, COSCO/OOCL, ZIM, Yang Ming, HMM) and public ship trackers (VesselFinder, MarineTraffic, MyShipTracking) | Not fetched by us. The user opens them in a new tab; their data, their terms. The container number check (ISO 6346) runs in the browser and sends nothing | n/a | Links only |
| gdelt | GDELT DOC 2.0 artlist, shipping/port disruption query, 14 days; deduplicated into incidents | GDELT open data, free with citation — https://www.gdeltproject.org/about.html#termsofuse ; dataset reuse, snapshots and redistribution permitted with citation/link; does not license publishers' full articles (checked 2026-11-07); max 1 request / 5 s | Source: The GDELT Project | Signal, not proof |

Live ship sources compared (2026-11-07): **aisstream.io** chosen (free key, live, server-side, any ship by MMSI near a coast).
AISHub needs your own AIS receiver to join. Global Fishing Watch covers fishing vessels only and is delayed.
Datalastic and MarineTraffic/VesselFinder APIs are paid (trials only). Map embeds load third-party scripts our CSP blocks.

# Flags
| Flag | Default | What it turns on |
|---|---|---|
| `CONFIRMATION_ENABLED` | `0` | The official-domain GDELT query, and "confirmed" events (which can raise an alert) |
| `AIS_ENABLED` + `AISHUB_USERNAME` | off | Ship counts near each port in the route answer |
| `AIS_LIVE_ENABLED` + `AISSTREAM_API_KEY` | off | Live position of one ship by MMSI in "Track it yourself" (`GET /api/vessel`) |
| `AIS_LIVE_WAIT_S` | `25` | Longest a ship lookup listens for a position report (3 to 60) |
| `REQUEST_GATE_WAIT_S` | `6` | Longest an answer waits for a free GDELT slot before using the cache or snapshot |

Every live GDELT call, from the refresher or from an answer, goes through one process-wide gate
(one call every 5.5 s). Only port names in `ports.py` are ever searched or cached; other names are
reported back as "we don't know that port yet".

# Dependency vetting
No third-party packages: stdlib `urllib`/`json`/`unittest` only. Nothing to pin or scan yet;
osv-scanner in CI still runs and exits 128 (no lockfiles), which the workflow accepts.

# Freshness and cache
Every result carries `source_updated_at` (when the data itself last changed) and `checked_at`
(when we fetched it), plus `mode` (`live` or `fallback`). Live fetches are cached in `CACHE_DIR`
(default `./.cache`): Met warnings 15 minutes, Holidays 7 days, ECB 1 day, CSO and Comext 31 days, GDELT 30 minutes. If a live fetch fails we
serve the stale cache, else the newest dated snapshot, both as `mode=fallback`. The cache holds
source results only, never user inputs. `SNAPSHOT_ONLY=1` is for tests and CI.
