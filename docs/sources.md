# Data sources

| source_id | Endpoint | Licence | Attribution | Role |
|---|---|---|---|---|
| cso_trade | CSO PxStat TSM06 (imports by SITC group, monthly, EUR thousand) | CC BY 4.0 — https://www.cso.ie/en/aboutus/whoweare/copyrightpolicy/ | Source: Central Statistics Office, Ireland | Context only |
| ecb_fx | ECB Data Portal EXR D.USD.EUR.SP00.A (daily reference rate) | ESCB free reuse policy — https://www.ecb.europa.eu/stats/ecb_statistics/governance_and_quality_framework/html/usage_policy.en.html (must not modify statistics) | Source: ECB statistics. | Rate series only |
| comext | Eurostat Comext DS-045409, reporter IE, HS 0901, extra-EU27, monthly value EUR + 100 kg | Eurostat free re-use, Decision 2011/833/EU / CC BY 4.0 — https://ec.europa.eu/eurostat/web/main/help/copyright-notice (exact Comext wording to confirm) | Source: Eurostat | Context only |

# Dependency vetting
No third-party packages: stdlib `urllib`/`json`/`unittest` only. Nothing to pin or scan yet;
osv-scanner in CI still runs and exits 128 (no lockfiles), which the workflow accepts.
