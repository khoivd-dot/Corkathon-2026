# Pitch and demo plan

## One-line idea

**In Time tells a small importer the date to place their next order, worked out from their own stock, holidays on both ends of the route, official Irish weather warnings and the euro rate, with every source dated.**

Short version: *"Will my imports be late or dearer this month? When must I order? Ask, and get a straight answer you can check."*

## Who it's for

**[Name], owner of a small homewares or coffee business in Cork/Dublin.** Buys goods from Shanghai or Santos, shipped through Rotterdam to Dublin or Cork (Ringaskiddy), invoiced in US dollars, rate not fixed. Has stock counting down and a multi-week shipping lead time.

Also for **their accountant at a firm like FRAME**, who wants to monitor order dates across 40 importing clients at once.

## Impact numbers

- **~49,600 Irish businesses imported goods in 2022; 98% are SMEs** (CSO, Ireland's Trade in Goods 2022).
- Any of them invoicing in dollars, sterling, yuan, yen or Swiss francs carries currency risk; anyone importing by sea is exposed to port disruption and holiday timing.
- Instead of an unanswerable "will it be late?", "when must I order?" gives a concrete deadline that goes directly into a diary.

## How it fits the judging (equal weight)

| Criterion | Our answer |
|---|---|
| **Innovation** | Joins Chinese New Year + Irish bank holidays + Met Éireann warnings + a business's stock count into one clear order-by date. Separates "reported" from "confirmed". Timing slider shows that the same data gives different answers in January vs June. |
| **Impact** | ~49,600 importers, 98% SMEs. An order-by date goes in a calendar (.ics export) without storing client data. Accountants can sort client books by order urgency. |
| **Technical depth** | Pure tested `compute_timing()` solver; licence-aware Met Éireann loader (verbatim, auto-expire); explainable regex parser ("no LLM invents numbers"); stdlib Python 3.12. |
| **Presentation** | Headline is a clear, actionable date ("Order by Sun 3 Jan."), not a shrug. Visual timeline strip, interactive date slider, verbatim weather notices. |

## Demo flows (3 minutes)

1. **Plain English (0:40–1:20):**
   - Type in ask box: *"I bring homewares from Shanghai through Rotterdam to Dublin in dollars, about 10 weeks of stock, takes 6 weeks to get here."*
   - The "We understood" chips appear and fill the form fields automatically.
   - Click "Check shipment".
   - **Expected Headline:** `Order by Sat 5 Dec.` (or `Order by Sun 3 Jan.` when tested with CNY window).
   - Under it: `28 days from today · No holidays on your route change this date.`

2. **January vs June ("Ask on another date", 1:20–1:50):**
   - Under the timeline, look at "Ask on another date". Today has 28 days left.
   - Tap quick chip **"20 Dec"**: Chinese New Year (6 Feb) enters the shipping window, pushing arrival past stock-out.
   - **Expected Headline:** `Order by Sun 3 Jan.`
   - Under it: `14 days from today · After that, Chinese New Year at Shanghai (6 Feb) pushes arrival past the day your stock runs out.`
   - Delta pill turns amber: `14 fewer days to order`.
   - Tap quick chip **"1 Jun"**: shipping window clears Chinese New Year.
   - **Expected Headline:** `Order by Tue 29 Jun.` (28 days left, delta pill: `Same as today`).
   - Quote sponsor brief: *"The same data means something different in January and June."*

3. **Live official data (1:50–2:15):**
   - Query or select Santos → Rotterdam → Cork.
   - The route card shows the verbatim **Met Éireann Official Notice**:
     `Status Yellow - Fog warning for Connacht, Leinster, Munster, Cavan, Monaghan` covering Cork (EI04).
   - Shows onset, expiry, and attribution to Met Éireann.
   - Open "Where this comes from" (or "Show working"): every source dated with live or snapshot label.

4. **Accountant workflow (2:15–2:35):**
   - Open Shipments book: shipments sorted with the most urgent order-by date first.
   - Click **"Add to calendar"** (`.ics` download) to set calendar alarms 2 days before the order date and on stock-out date.
   - Click **"Copy for my accountant"** to copy client summary with sources.
   - Pitch line: *"FRAME sends this to 40 importing clients on Monday morning."*

5. **Limits & Close (2:35–3:00):**
   - Rule-of-thumb buffers are explicitly labelled. Met warnings look ahead ~48 h. ECB isn't your bank's rate. We can't see your specific container.

## Three-minute script

| Time | Who | What |
|---|---|---|
| 0:00–0:25 | Pitcher | Importer's story: finding out too late when stock runs out. |
| 0:25–0:40 | Pitcher | The solution: answering *when* to order, not *whether* it will be late. |
| 0:40–1:20 | Developer | Flow 1: Plain English input → chips fill form → Order-by headline. |
| 1:20–1:50 | Developer | Flow 2: January vs June slider — 28 days becomes 14 because of Chinese New Year. |
| 1:50–2:15 | Developer | Flow 3: Live Met Éireann weather warning on the route to Cork. |
| 2:15–2:35 | Developer | Flow 4: Accountant shipments book sorted by urgency + .ics export. |
| 2:35–3:00 | Pitcher | Limits, privacy (nothing stored), and close: "Now they know in time." |

## Demo safety checklist

- [ ] Run `make snapshot` the morning of the demo to ensure fresh cache/snapshots.
- [ ] Run the app locally (`SNAPSHOT=1 PYTHONPATH=src python3 -m corkathon.server`) as well as online.
- [ ] Rehearse with `SNAPSHOT_ONLY=1` in case Wi-Fi fails; Met warnings and holidays demo cleanly from snapshot.
- [ ] Record a backup screen video once flows 1–4 are validated.
- [ ] Zoom the browser so the back row can read it; test in light and dark mode.

## Likely judge questions & answers

- *"Why not an LLM?"*
  → The regex parser is completely explainable, deterministic, and cannot hallucinate or invent numbers. In logistics and financial accounting, hallucinated lead times or dates cause real business losses. With more time, an LLM could assist in conversational summarization, but the calculation engine must remain pure, tested mathematics.
- *"Hasn't this been done before?"*
  → Enterprise software like Resilinc or Project44 serves Fortune 500 logistics teams. Small Irish SMEs and their accountants have nothing comparable: In Time gives them a clear order-by date in plain English without complex ERP integration.
- *"How is this different from a news alert?"*
  → Instead of vague news, it solves the inverse problem: "When is the absolute latest date I must place an order before my stock runs out?" factoring in origin holidays, destination holidays, and weather warnings.
- *"Why Met Éireann and Nager.Date?"*
  → Met Éireann is official open Irish data listed on data.gov.ie as a High Value Dataset. Nager.Date provides MIT-licensed worldwide public holidays matching port UN/LOCODEs.
- *"What about client privacy?"*
  → Zero user data is stored, cached, or logged. Everything runs in-memory and in the user's browser session. Calendar exports (.ics) are generated entirely client-side.
