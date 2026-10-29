<p align="center"><img src="media/petlife-life.png" alt="PetLife: less digging through messages, more time with your pets." width="100%"></p>

# PetLife 🐾 Less remembering. More pet time.

**Who fed the cat? Which batch should we open first? Did I already record this receipt? What should I bring to the vet?**

An Agent Skill for real cats and dogs. Turn labels, receipts, caregiver messages and owner observations into sourced local records your Agent can continue using next time.

[中文](README.md) · [Reproducible scenarios](examples/everyday/README.md) · [Skill instructions](SKILL.md) · [Evidence and design rationale](references/market-and-evidence.md)

![Skill checks](https://github.com/l422145205-source/pet-life/actions/workflows/ci.yml/badge.svg)

## Install once, keep using your usual Agent

```sh
npx skills add l422145205-source/pet-life
```

Use an Agent that can access local files and execute Python. The helpers require Python 3.10+ standard library only: no model service, database or API key. Image reading comes from the host Agent; transcribed label text works too.

> Use `$pet-life` to organize these pet records. Review food batches and the sitter handoff first. Keep unresolved details visible and save the ongoing record in this workspace's `.pet-life/household.json`; don't upload it.

No complete form is required upfront. A later session needs access to the same file; there is no cloud memory or cross-device sync.

## What does installing the Skill add?

| Task | Packaged behavior |
| --- | --- |
| Continue tomorrow | A stable local record format plus append-only merge tools; exact event replays are no-ops, conflicting IDs and stale file hashes stop the write |
| Count supplies and spending | Explicit units, end-of-day stock counts, receipt reconciliation and source references |
| Plan batches | Date-constrained allocation within the same product, showing near-date surplus and planning shortfalls |
| Coordinate care | Per-pet/time plans distinct from caregiver reports; missing, conflicting and multiple completion reports remain distinct |
| Prepare for a vet visit | A sourced observation timeline, supplied current care/therapy details and visible gaps |

Ordinary chat can do these tasks with equivalent instructions, files and tools. Installation packages that setup for reuse; it does not add a new model or prove better model intelligence. The host Agent handles interpretation, while the Skill supplies task rules and executable operations.

<img src="media/workflow.gif" alt="Workflow: supplied materials, Agent fact checking, reusable tools, records that can be continued." width="100%">

The animation illustrates synthetic data and actual helper results. It is not an Agent screen recording. The Chinese scenario cards below link to inspectable outputs.

## Seven everyday requests

| Ask your Agent | What you get | Example |
| --- | --- | --- |
| “Plan next week's food from these batch counts and dates.” | Within-product ordering, date-limited surplus, a planning gap; no invented universal shelf life after opening | [Batch report](examples/everyday/stock.md) |
| “Two caregivers disagree about tonight's feeding.” | Separate reports, conflicts and unrecorded slots; no assumption that missing check-ins mean missed feeding | [Care checklist](examples/everyday/care.md) |
| “Summarize the last two weeks for our vet.” | Literal owner observations, dates, sources and pending reports; unknown therapy details stay unknown | [Visit brief](examples/everyday/visit.md) |
| “Record this receipt; I may have sent it yesterday.” | Stable event IDs, idempotent replay and guarded local writes | [Receipt replay](examples/everyday/replay.md) |
| “Compare the paid prices; the bag sizes changed.” | Unit-price arithmetic with explicit package size; calorie comparisons only from supplied label calories | [Budget brief](examples/brief.md) |
| “Prepare a three-day sitter handoff.” | Per-pet quantities, places, separation instructions and visible missing essentials | [Handoff](examples/care-card.md) |
| “Write a cat-boss monthly expense review.” | Playful wording around sourced spending and recorded activities; no invented life events | [Synthetic source packet](assets/source-packet.example.md) |

Dogs are included: [a fictional walk/water handoff](examples/everyday/dog/care.md) preserves the owner's existing instructions and a caregiver's request for help. It does not prescribe exercise duration.

<img src="media/everyday-results.png" alt="Synthetic results: a one-can planning gap, one care-report conflict and one unrecorded slot, three confirmed observations and one pending report, and receipt replay of 209 to 221 to 221 CNY." width="100%">

All animals, products, caregivers and events are synthetic. The tool actually produces these results: seven cans by volume can leave a one-can date-constrained planning gap; a repeated receipt changes spending **209 → 221 → 221 CNY** with zero new entries on replay. These are reproducible helper behaviors, not model benchmark scores or real customer outcomes. [Inputs and outputs](examples/everyday/README.md).

<img src="media/batch-calendar.png" alt="Synthetic seven-can calendar: date constraints leave one can outside the owner's existing consumption plan and a one-can planning gap on the final day." width="100%">

## Why these scenarios?

Industry research describes more considered pet spending and demand for transparent information; this informed paid-price records and sourced life summaries. Care-service concerns informed the distinction between promised routines and reported actions. These are design inferences from desk research, not user interviews or demonstrated market fit. [KPMG industry report](https://kpmg.com/cn/zh/insights/2025/06/2025-china-pet-industry-market-report.html), [iiMedia 2026 insights](https://www.iimedia.cn/c1086/117998.html).

[FDA food-storage guidance](https://www.fda.gov/animal-veterinary/animal-health-literacy/proper-storage-pet-food-treats) supports retaining batch/date information; [AAHA senior-care guidance](https://www.aaha.org/resources/2023-aaha-senior-care-guidelines-for-dogs-and-cats/evaluating-the-healthy-senior-pet/) supports collecting daily-history and current-therapy details. Those sources guide record keeping, not a claim of clinical validation. [Scope and limitations](references/market-and-evidence.md).

## Try the outputs without a model

Clone the repository, then:

```sh
python tools/reproduce.py --out work/demo
python -m unittest discover -s tests -v
```

This produces budget, sitter, batch, care and visit outputs plus the cross-call receipt replay. [Base schema](references/record-format.md) · [Extended workflows and update commands](references/everyday-workflows.md) · [Media regeneration](tools/README.md).

The runtime scripts make no network calls. Only an explicit `merge --write` updates the chosen local ledger; report commands leave it untouched. Inventory and check-ins are reported records, not physical monitoring. Batch dates do not establish food safety and no recall search is performed. Use existing owner instructions; no new diet, diagnosis, medication dose or health score is generated. Vet preparation should not delay seeking veterinary help. The host service has its own data handling.

## Help the next pet owner find it

Try one supply check, care handoff or visit brief and [share a redacted example](https://github.com/l422145205-source/pet-life/issues) of what still feels cumbersome. Please keep personal contacts, raw receipts and clinical records out of public issues. If the idea is useful, a Star or a shared scenario card helps other pet owners find it. MIT licensed.
