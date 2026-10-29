<p align="center"><img src="media/petlife-banner.svg" alt="PetLife: less pet paperwork, more time with your pets" width="100%"></p>

# PetLife 🐾 More cuddles. Less pet paperwork.

**An Agent Skill that turns food labels, shopping receipts and “here's their usual routine” into a useful care record.** For real cats and dogs.

[中文](README.md) · [Skill instructions](SKILL.md) · [Worked example](examples/agent-example.md) · [Computed brief](examples/brief.md)

## Your suitcase is packed. Your sitter has one more question.

“Which cat gets which bowl? How much food? Is that half a can each, or half a can total?”

The answers are somewhere in a chat, on the back of a food bag, and in a receipt you may have uploaded twice. PetLife gives your Agent a workflow for gathering those fragments, checking the units, doing the arithmetic and handing back something a person can actually use.

```sh
npx skills add l422145205-source/pet-life
```

Then ask your Agent:

> Use `$pet-life` to organize these labels, receipts and owner notes. Both cats share a bag. How long will the food last, what spending is recorded this month, and what should I pack for a three-day sitter handoff? Keep the blurry receipt unresolved.

The host Agent supplies language and any image understanding. PetLife adds the task workflow, record format and a **Python 3.10+ standard-library helper**. No additional model service or database.

## Three pet-owner headaches, one Skill

**“Didn't I just buy food?”** Combine household stock while keeping each pet's existing daily quantities separate. Normalize explicit package sizes and calorie units; compare actual paid prices. A repeated receipt counts once. Unknown prices stay unknown.

**“Please don't make my friend guess.”** Produce a pet-by-pet sitter card: quantities, feeding location, times, quirks and packing amounts. Missing emergency arrangements keep it a draft. The Skill transcribes the owner's routine; it does not prescribe a new diet.

**“Who is funding whose lifestyle?”** Ask for a playful pet-POV monthly brief with real source-backed numbers. The joke can be dramatic. The spending cannot. Recorded purchases remain separate from projected daily costs.

## Follow one example from messy notes to actual files

The synthetic household has two cats, one shared bag, a repeated receipt, an unconfirmed purchase and a future record. The helper computes:

- CNY **209** in recorded period spending.
- About **25.7 days** of dry-food book coverage; **7 days** of wet food.
- CNY **13.22/day** at the supplied routine and latest recorded prices.
- **270 g dry food and 3 cans** for a three-day handoff, split by pet; missing emergency details remain visible.

These are fictional example records, not customer results or a hidden benchmark. [Source packet](assets/source-packet.example.md) → [normalized input](assets/household.example.json) → [computed brief](examples/brief.md) / [sitter card](examples/care-card.md). Sample outputs are in Chinese; the Skill instructs the Agent to answer in the user's language.

Clone this repository and reproduce the calculation:

```sh
python scripts/petlife.py build --input assets/household.example.json --as-of 2026-10-03 --trip-days 3 --out work/example
```

The helper writes `brief.md`, `care-card.md` and `report.json`; it does not perform OCR or edit the input ledger. [More prompt ideas and the full walkthrough](examples/agent-example.md)

## What it keeps straight

| Easy to mix up | PetLife's rule |
| --- | --- |
| kg vs g; per-can vs per-kg calories | Convert only when the label explicitly supplies the measure |
| One package vs several packages in an order | Normalize receipt quantity and package size separately |
| Original price vs actual paid price | Use paid amounts; leave unallocated discounts unresolved |
| Duplicate upload vs another purchase | Reuse stable receipt/line IDs; conflicting IDs need reconciliation |
| Spending this month vs estimated cost per day | Report them separately |
| Book stock vs food physically in the cupboard | Show the last count date and the effect of missing logs |

Records stay in the selected workspace. The helper makes no network calls or automatic messages; the host Agent follows the data practices of your chosen service. Use redacted or synthetic examples in public Issues. Existing owner quantities support bookkeeping and packing, not medical prescriptions. [Record format](references/record-format.md) · [Primary label sources](references/labels-and-care.md)

Bring a real-life pet chore and a redacted example to [Issues](https://github.com/l422145205-source/pet-life/issues). If this saves you a few trips through your chat history, a **Star** helps the next pet owner find it.

MIT licensed. Checks: `python -m unittest discover -s tests -v`.
