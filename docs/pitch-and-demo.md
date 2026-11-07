# Pitch and demo plan

> Draft, updated 11:50 for the importer direction and the live decision engine. Fill in the [brackets]. Owner: Isabelle.

## One-line idea

**For Ireland's ~49,000 small importers, who find out about port strikes and currency swings too late, we check their own shipping route against live news, official port and carrier notices and ECB exchange rates, and tell them in plain English whether their imports will be late or dearer, with one next step and every source dated.**

Short version: *"Will my imports be late or dearer this month? Ask, and get a straight answer you can check."*

## Who it's for

**[Name], owner of a small coffee roaster in Cork.** Buys green beans from Brazil, shipped Santos → Rotterdam → Cork (Ringaskiddy), invoiced in US dollars, rate not fixed. Has three weeks of stock; a new order takes five weeks to arrive. Hears about a Rotterdam strike on the radio a week after it started.

Also for **their accountant at a firm like FRAME**, who wants to warn several importing clients at once.

## Impact numbers

- **~49,600 Irish businesses imported goods in 2022; 98% are SMEs** (CSO, Ireland's Trade in Goods 2022).
- Any of them invoicing in dollars, sterling, yuan, yen or Swiss francs carries currency risk; anyone importing by sea is exposed to port disruption.
- Coffee example: ~3,500 cafés in Ireland depend on importers and roasters like [Name] (business listings, not official).

## How it fits the judging (equal weight)

| Criterion | Our answer |
|---|---|
| **Innovation** | Joins sources nobody combines for a small business: the user's own route + global news + official carrier/port notices + ECB rates. Separates "reported" from "confirmed". Not a dashboard: one answer, one next step. |
| **Impact** | ~49,600 importers, 98% SMEs. Earlier warning on the two things that hurt cash flow: late stock and dearer invoices. |
| **Technical depth** | Real live data, route-matched filtering, duplicate merging, confirmation rules, decision engine, cache with fallback, nothing the user types is stored, 77 tests. |
| **Presentation** | Live form → answer card from the real server; "Show working" table proves the data drives the result. |

## Demo flows

**Important:** the live app has confirmation switched off (`CONFIRMATION_ENABLED=0`) until the carrier and port advisories' reuse terms are checked. So **live, it never raises an alert**: every event is "reported". Plan the demo around that; it's a strength, not a gap. Rehearse all three.

1. **Live: the honest answer.** Example Coffee Ltd, Santos → Rotterdam → Cork, USD, rate not fixed, 21 days stock, 35 days lead time.
   → *"We can't determine whether your shipment is affected."* It still says your stock runs out 14 days before a new order would arrive and tells you to ask your forwarder for an ETA. It lists any news reports on your route as "not confirmed", and names the ports it can't check (Rotterdam, Cork…) with links to their official notices. Open **Show working**: every source with its date, and the line "Checked 11:05 UK time. Trade figures are August data…". Say out loud: *"It never says 'No action needed' when it doesn't know."*
2. **Live: the currency answer.** Same inputs → the cost card shows how much dearer the unfixed part of the invoice is in euro since a month ago, and that it's not your bank's rate. Switch to euro, or rate fixed for "all" → no exchange-rate exposure.
3. **What a confirmed alert looks like** (example data, clearly labelled). The saved 7 Nov example "confirmed event on route" → *"Check your forwarder's ETA today: your stock runs out 14 days before a new order would arrive."* Explain: this switches on once official advisory feeds are cleared for reuse.

Write the expected result for each before demo day so you can spot a bug.

## Three-minute script

| Time | Who | What |
|---|---|---|
| 0:00–0:25 | Pitcher | [Name]'s story: heard about the Rotterdam strike a week late; stock ran out. |
| 0:25–0:40 | Pitcher | One-line idea and the 49,600 importers. |
| 0:40–1:40 | Developer | Flow 1 live: fill in route; honest answer, stock shortfall, ports to check; open Show working. |
| 1:40–2:05 | Developer | Flow 2 live: the currency card; switch to euro. |
| 2:05–2:25 | Developer | Flow 3: the confirmed alert (example), and what switches it on. |
| 2:25–2:45 | Pitcher | Honest limits: news is a signal; ECB isn't your bank's rate; we can't see your specific ship. |
| 2:45–3:00 | Pitcher | What's next and close: "Late or dearer? Now they know in time." |

## Demo safety checklist

- [ ] Run `make snapshot` (or the PowerShell version) the morning of the demo.
- [ ] Run the app locally (`python -m corkathon.server`, see architecture.md) as well as on Render, in case either fails.
- [ ] Rehearse with `SNAPSHOT_ONLY=1` in case the Wi-Fi fails; the screen labels data as a saved copy.
- [ ] Don't share the Render link publicly without Tran's yes.
- [ ] Record a backup screen video once flows 1–3 work.
- [ ] Zoom the browser so the back row can read it; test in dark mode too.
- [ ] Check the submission deadline and what has to be uploaded.
- [ ] Nothing public or sent outside the team without Tran's yes.

## Likely judge questions

- *"How is this different from a news alert?"* → It's matched to your route and dates, separates rumour from confirmation, and ties it to your own stock and invoice.
- *"How do you know the strike affects my ship?"* → We don't, and we say so. We tell you to check with your forwarder, with the reason.
- *"Why didn't it raise an alert?"* → Because no official source has confirmed it. We only alert on a carrier or port notice, and we won't use those until their reuse terms are checked. Until then we say what we can't check and link you to it.
- *"Why ECB rates, not market rates?"* → Official, free, reusable; we say clearly it's not your bank's rate.
- *"What about my data?"* → What you type is never saved or logged; the cache holds public data only.
- *"Who pays?"* → [e.g. accountancy firms offering it to importing clients].
- *"What would you add with more time?"* → Ship tracking (once display rights are clear), more confirming sources, alerts when something changes, testing with real importers.
