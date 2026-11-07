# Data sources

| source_id | Endpoint | Licence | Attribution | Role |
|---|---|---|---|---|
| cso_trade | CSO PxStat TSM06 (imports by SITC group, monthly, EUR thousand) | CC BY 4.0 — https://www.cso.ie/en/aboutus/whoweare/copyrightpolicy/ | Source: Central Statistics Office, Ireland | Context only |
| ecb_fx | ECB Data Portal EXR D.USD.EUR.SP00.A (daily reference rate) | ESCB free reuse policy — https://www.ecb.europa.eu/stats/ecb_statistics/governance_and_quality_framework/html/usage_policy.en.html (must not modify statistics) | Source: ECB statistics. | Rate series only |
| comext | Eurostat Comext DS-045409, reporter IE, HS 0901, extra-EU27, monthly value EUR + 100 kg | Eurostat free re-use, Decision 2011/833/EU / CC BY 4.0 — https://ec.europa.eu/eurostat/web/main/help/copyright-notice ; statistical reuse incl. commercial display and snapshots permitted with acknowledgement; identify modifications and apply Eurostat's disclaimer (checked 2026-11-07) | Source: Eurostat | Context only |
| gdelt | GDELT DOC 2.0 artlist, shipping/port disruption query, 14 days; deduplicated into incidents | GDELT open data, free with citation — https://www.gdeltproject.org/about.html#termsofuse ; dataset reuse, snapshots and redistribution permitted with citation/link; does not license publishers' full articles (checked 2026-11-07); max 1 request / 5 s | Source: The GDELT Project | Signal, not proof |

# Dependency vetting
No third-party packages: stdlib `urllib`/`json`/`unittest` only. Nothing to pin or scan yet;
osv-scanner in CI still runs and exits 128 (no lockfiles), which the workflow accepts.

# Freshness and cache
Every result carries `source_updated_at` (when the data itself last changed) and `checked_at`
(when we fetched it), plus `mode` (`live` or `fallback`). Live fetches are cached in `CACHE_DIR`
(default `./.cache`): ECB 1 day, CSO and Comext 31 days, GDELT 30 minutes. If a live fetch fails we
serve the stale cache, else the newest dated snapshot, both as `mode=fallback`. The cache holds
source results only, never user inputs. `SNAPSHOT_ONLY=1` is for tests and CI.
