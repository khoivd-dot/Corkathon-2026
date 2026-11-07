# Project plan

> Living plan for Corkathon 2026, updated 11:50. Fill in the [brackets]; the event schedule isn't in the repo.

## Goal

By the demo, a small Irish importer enters one shipment route and gets a sourced, dated, plain-English answer to "Will my imports be late or dearer this month?", with one next step, running on real data.

## Key times

| What | When |
|---|---|
| Hacking started | Sat 7 Nov, ~09:50 |
| Concept chosen | ~10:45 (coffee imports), broadened ~11:25 to any importer |
| Code freeze | [submission deadline minus 1 hour] |
| Submission deadline | [check with organisers] |
| Demo / judging | [check with organisers] |

## Roles

| Person | Role | Owns |
|---|---|---|
| Tran | Decision-maker | Concept; approves every merge and anything public |
| Khoi (khoivd-dot) | Engineering Lead | Architecture, code review, merges |
| Design Lead | Design | Screens, accessibility, mockups (PR #8) |
| SWE bot (Grok) + Claude Code | Builders | Loaders, events, inputs, exposure, tests |
| Isabelle | Product, data and pitch | Docs, impact numbers, demo flows, Limits, pitch, submission |
| [others] | | |

## Milestones

| # | Milestone | Done when | Status |
|---|---|---|---|
| M0 | Repo set up | Rules, CI | ✅ 10:06 |
| M1 | Concept | One-line idea agreed by Tran | 🟡 importer direction clear; wording to confirm |
| M2 | Data loaders | ECB, GDELT, CSO, Comext on `main` | ✅ 10:55 |
| M3 | Shared base (PR A) | Cache, fallback, freshness fields | ✅ 11:22 (#9) |
| M4 | User inputs (PR C) | Validated, in memory, plain wording | ✅ 11:24 (#10) |
| M5 | Exposure (PR D) | Stock buffer + FX on unfixed share | ✅ 11:26 (#12); 5 currencies 11:30 (#13) |
| M6 | Events (PR E) | Route-matched, reported vs confirmed | ✅ 11:11 (#7) |
| M7 | Screen | Form + answer card, accessible | ✅ 11:37 (#8) |
| M8 | Decision + wiring | Live inputs → events + exposure → headline and next step on screen | ✅ 11:40 (#15), page reads `/api/answer` 11:43 (#17) |
| M8b | Deployment | Render config, server, health check | 🟡 configured (#16); deploy waits on Tran's yes |
| M8c | Confirmation sources | Reuse terms recorded for carrier/port advisories; `CONFIRMATION_ENABLED` on | ⬜ (off until then) |
| M9 | Docs | Plan, architecture, sources, pitch, contributing | ✅ 11:35 (#14); this update pending |
| M10 | Demo ready | 3 flows rehearsed, snapshots fresh, backup video | ⬜ |
| M11 | Submitted | Repo, README, Limits, video, form | ⬜ |

## Work breakdown

### Engineering
- [x] Loaders, PR A base, inputs, exposure, events, multi-currency FX
- [x] Screen (#8), decision engine (#15), server and page wired to `/api/answer` (#17)
- [x] Render config, auto-deploy off (#16)
- [ ] Deploy, once Tran says yes
- [ ] Record reuse terms for carrier/port advisories, then decide on `CONFIRMATION_ENABLED`
- [ ] Freshness warning rule per source (when is data too old to show without a warning?)
- [ ] Decide on `LLM_ENABLED`: if used, may only reword computed facts, never add numbers
- [ ] End-to-end test: form → answer JSON

### Product, data and pitch (Isabelle)
- [x] Limits section in README
- [x] Docs v1 (#14)
- [x] Impact numbers: ~49,600 importers, 98% SMEs (CSO 2022)
- [ ] Docs v2 for importer direction (this PR)
- [ ] Update README Limits for importer scope (see below)
- [ ] Try the live app as a non-expert: is every form question and answer clear?
- [ ] Confirm one-line idea with Tran
- [ ] Write expected results for the 3 demo flows
- [ ] Slides (3–4 max) and script; rehearse twice; backup video
- [ ] If possible, ask a FRAME mentor: "Would your importing clients use this?"
- [ ] Submission form and links

## Suggested timeline

| Block | Engineering | Product / pitch |
|---|---|---|
| Now → +1 h | Deploy (with Tran's yes); end-to-end test | Docs v2; try the live app as a user; confirm one-liner |
| +1 h → +3 h | Advisory reuse terms; freshness warnings | Slides, script, mentor feedback |
| +3 h → +5 h | Freshness warnings; polish; accessibility pass | Update Limits and docs to match the build |
| +5 h → freeze | Bug fixes; fresh snapshots | Rehearse; backup video |
| Freeze → deadline | Fixes only | Submit |

## Decisions log

| When | Decision | By |
|---|---|---|
| 10:06 | Every change via small PR; merges need Tran's OK | Team |
| ~10:45 | Python 3.12, standard library only | Engineering |
| ~10:45 | Loaders never fail; fall back to cache, then snapshots | Engineering |
| 11:07 | Never infer the user's route; no ports → no events | Engineering |
| 11:09 | News alone is "reported"; "confirmed" needs a carrier/port advisory naming an event and a place on the route | Engineering |
| ~11:20 | Scope: any small importer, coffee as worked example | Team |
| 11:24 | User inputs are never stored or logged | Engineering |
| 11:26 | FX is a separate answer; never implies delay; no default fixed share | Engineering |
| 11:30 | Currencies: EUR, USD, GBP, CNY, JPY, CHF | Engineering |
| 11:40 | Confirmation off (`CONFIRMATION_ENABLED=0`) until advisory reuse terms are recorded; never say "No action needed", abstain instead and list ports we can't check | Team |
| 11:41 | Render Starter + 1 GB disk; auto-deploy off; deploy needs Tran's yes | Tran |
| | AIS ship tracking not used: display rights unverified | Engineering |
| | [AI model for wording: yes / no] | |

## Risks

| Risk | Likelihood | Impact | Plan |
|---|---|---|---|
| Live app never alerts (confirmation off) | Certain | Medium | Present the honest answer as the feature; show the alert from labelled example data |
| Wi-Fi fails during demo | Medium | High | `SNAPSHOT_ONLY=1`; backup video |
| Hosted app down during demo | Low | High | Run locally as a backup; backup video |
| News matches irrelevant stories | High | Medium | Show as "reported", link sources, never alert on reports alone |
| Users misread ECB rate as their bank's rate | Medium | Medium | Card says so explicitly |
| Scope creep | Medium | High | Three demo flows only; everything else under "with more time" |
| Merging without Tran's OK | Happened | Medium | Ask before clicking Merge |
| Answer shown without source/date | Low | High (team rule) | "Show working" table on every answer; test for it |

## Definition of done (for the demo)

- Three flows work: live honest answer, live currency card, labelled example alert
- Every figure shows source and date; fallbacks labelled as saved copies
- Works with Wi-Fi off
- Nothing the user types is stored
- README explains the idea, how to run it, and its limits
- CI green on `main`
