# Brand

## Name

**In Time**

*Find out before your stock runs out.*

- Says the benefit, not the technology. An importer's real fear is finding out too late.
- Short, plain English, easy to say on stage.
- The question the product answers stays as the page heading: **"Will my imports be late or dearer?"**
- Currently the page header says "Imports check". Proposed: "In Time" in the header and `<title>`, with the question kept as the main heading.

## Voice

| Do | Don't |
|---|---|
| Plain English a busy owner reads in 10 seconds | Logistics or finance jargon ("transshipment exposure") |
| Say when we don't know: "We can't determine whether your shipment is affected." | Reassure without evidence: never "No action needed" |
| One next step, in the imperative: "Ask your forwarder for a current ETA." | Lists of options or vague advice |
| Name the source and date of every number | Unsourced figures or "real-time" claims |
| Separate rumour from fact: "reported" vs "confirmed" | Alarmist words: "crisis", "urgent", red-alert styling |
| Say what isn't ours: "This isn't your bank's rate." | Imply we see the user's own container or bank |

Example headline: *"Check your forwarder's ETA today: your stock runs out 14 days before a new order would arrive."*

## Colour

From the app's design tokens (`web/styles.css`, defined in OKLCH; hex values are close equivalents for slides and documents). Light and dark follow the reader's system setting.

| Role | Token | Light | Dark | Used for |
|---|---|---|---|---|
| Background | `--background` | `#FBFAF7` | `#1D222A` | Page |
| Card | `--card` | `#FFFFFF` | `#282E38` | Cards, answer, form |
| Soft fill | `--secondary` | `#F2F0ED` | `#323844` | Chips, charts, inner panels |
| Text | `--foreground` | `#1A1F29` | `#F3F5F9` | Body, headings |
| Muted text | `--muted-foreground` | `#58554F` | `#BFC4CE` | Captions, "How sure" |
| Brand (blue) | `--brand` | `#245FD4` | `#73A3FC` | Main buttons, links, sliders, route line, focus, accent panels (soft tint) |
| Data (green) | `--data` | `#0E8C41` | `#53DE73` | Stock bar, exchange-rate line |
| Warning (amber) | `--warn` | `#C66000` | `#FCA942` | Stock shortfall, confirmed event |
| Calm | `--calm` | `#007E46` | `#60DB89` | "About the same", nothing to act on |
| Unknown | `--unk` | `#566286` | `#A8B6DF` | "Nothing reported", can't tell |

Rules:
- **Amber means "act", not "danger".** There is no red status colour: the product warns, it doesn't alarm.
- **Colour never carries meaning alone.** Every status has a word and an icon ("⚠ 14 days short").
- **No heavy dark colours** (Khoa, 7 Nov): dark mode is a soft blue-tinted charcoal, not pure black; buttons and accent panels use the brand blue, not black.
- **Contrast:** WCAG 2.2 AA in both themes (the team rule; the page passes automated checks with 0 violations).

The pitch deck still uses the old Night Harbour colours (navy `#13233A`, off-white `#F6F3EC`, amber `#E8913A`) and needs updating to match.

## Typography

| Use | App | Deck |
|---|---|---|
| Display and headlines | **Inter Display** SemiBold, tight tracking (self-hosted, OFL) | Inter |
| Body and interface | **Inter** Regular, Medium, SemiBold (self-hosted, OFL) | Inter |

- Headlines in sentence case, no full stops on labels.
- Status words big and short: "14 days short", "Nothing reported", "About the same".
- Numbers always with units and dates: "ECB rate as of 6 Nov".

## Logo

Not required for judging; a wordmark is enough.

- **Wordmark:** "In Time" in Inter Display SemiBold, in `--foreground`, with the blue arc already used in the page header placed before it, as a horizon or the edge of a clock.
- **Clear space:** the height of the capital "I" on every side.
- **Don't:** add ships, containers, globes or clocks with hands; recolour the wordmark in a status colour.

## Where the brand appears

| Place | Status |
|---|---|
| Pitch deck (10 slides) | Uses "In Time" |
| README title | To change, with Khoi's OK |
| Page header and `<title>` (`web/index.html`) | To change, with Khoi's OK |
| `CLAUDE.md` | Optional pointer, so agents follow this file: *"For the product name, wording and colours, follow docs/brand.md."* Khoi's call |
