# Repeatable real-pet workflows

Read this for batch planning, caregiver check-ins, visit preparation, or local ledger updates. Use only fields needed for the request. The complete **synthetic** structure is [everyday.example.json](../assets/everyday.example.json); retain the [base record rules](record-format.md).

## Local records across conversations

Prefer a user-chosen `.pet-life/household.json` in the task workspace. The Skill supplies a record format and file tools; it does not provide cloud memory, cross-device sync or background reminders. A new Agent session must have access to the same file. Do not scan unrelated personal folders.

For an owner request to record a receipt, observation or completed care task:

1. Inspect the existing file and retain its SHA-256:
   `python <skill-dir>/scripts/carekit.py inspect --input <household.json>`
2. Extract a patch with one or more of `records`, `observations`, `completions`. Stable IDs identify source events; use receipt ID plus line, or a source ID assigned once and retained. Same price is not evidence of the same purchase. OCR ambiguity stays pending.
3. Preview if useful:
   `python <skill-dir>/scripts/carekit.py merge --input <household.json> --patch <patch.json> --as-of YYYY-MM-DD --out <preview.json>`
4. When the user requested local persistence, apply with the inspected hash:
   `python <skill-dir>/scripts/carekit.py merge --input <household.json> --patch <patch.json> --as-of YYYY-MM-DD --write --expect-sha256 <hash>`
5. Refresh only the requested reports. Return what was added and any unresolved facts.

Same ID + same contents is a no-op; same ID + changed contents fails. A changed hash or busy lock fails without an overwrite. Re-read and reconcile once rather than retrying a stale write. The lock coordinates these tools; an unrelated editor need not honor it. Atomic replacement avoids partially written JSON. This is local persistence, not a database transaction spanning other apps.

Append patches cannot overwrite pet profiles, stock snapshots, instructions or prior event contents. For a correction, first reconcile the original source with the owner, then make an explicit targeted edit in the chosen file and regenerate reports; never silently reassign a receipt ID. After receiving a user-requested factual correction, no extra approval is needed just because the helper is append-only.

## Batch and opening-date review

`batches[]` entries require `id`, `product_id`, `remaining`, `unit`, `counted_on` (end of day), `source`. Optional: `lot_code`, `best_before` (date copied from label), `opened_on`, `storage_note`, `quality_hold` (boolean). An owner's explicitly supplied review/use-by date goes in `owner_use_by` with `use_by_source`. Do not invent one from opening date. Copy the label's exact wording to local source notes; hour-level storage instructions remain explicit manual checks, not day-level conversions.

`batch_inventory_complete:true` means the owner explicitly confirmed all current batches of the listed products were counted. It does not establish product safety. Counts from another date, unknown deadlines, or held batches are excluded from the date-constrained plan and keep the basis incomplete. The plan uses only a same-day physical count; the purchase ledger remains separate and may disagree if consumption is missing. Explain the discrepancy instead of adding them together.

```sh
python <skill-dir>/scripts/carekit.py stock --input <household.json> --as-of YYYY-MM-DD --days 7 --out <output-folder>
```

The tool simulates the **following** 1–90 days, using earlier supplied dates first within the **same product**. Dates are inclusive at date resolution. It reports batch allocations, date-limited surplus, and a planning shortfall rounded to package equivalents. Incomplete records yield a provisional difference, not an instruction to purchase. No daily amount means no forecast. Do not increase feeding or swap therapeutic diets to use up stock. No recall lookup, food-safety guarantee, physical monitoring or ordering is performed.

## Multi-caregiver check-ins

`care_tasks[]`: `id`, `pet_id`, `title`, `time` (`HH:MM`), `instructions`, `source`. One task is one daily slot; split each pet and time. These are explicit existing owner instructions, not model-generated feeding or medication schedules. If a medication instruction is included, preserve its supplied exact text and source; never supply a missing dose.

`completions[]`: `id`, `task_id`, `date`, `status` (`done`, `skipped`, `needs_help`), `actor` (local alias), `source`.

```sh
python <skill-dir>/scripts/carekit.py care --input <household.json> --as-of YYYY-MM-DD --days 3 --out <output-folder>
```

The report includes the as-of day at day-end and the following days. No log is **not_recorded**, not proof that care was missed. Two distinct reports on the same slot require review, including two “done” reports (possible duplicate care). Conflicting statuses are not resolved by “last writer wins”. A future dated completion is flagged for review, never accepted as accomplished care. A check-in does not prove the pet ate, deduct inventory or send a message. Confirm a conflict before any repeat feeding.

## Vet-visit observation brief

`observations[]`: `id`, `pet_id`, `observed_on` (`YYYY-MM-DD`), `category`, literal owner `text`, `source`; optional `confirmed:false`. Optional quantitative `value` requires `unit` alongside it. Keep the observation text and measurement conditions even when a number is available. Do not infer clinical trends from incomparable measurements.

`current_therapies[]`: `id`, `pet_id`, supplied literal `text`, `source`. Missing entries mean unknown, not “no medication”.

```sh
python <skill-dir>/scripts/carekit.py visit --input <household.json> --as-of YYYY-MM-DD --start YYYY-MM-DD --out <output-folder>
```

The default window is 14 calendar days. Outputs group records by pet, separate confirmed observations from pending reports, exclude future entries, list current supplied food/therapy information and questions to bring to a vet. Missing days do not imply uninterrupted symptoms or absence. Do not diagnose, invent urgency scores or reassure from an incomplete summary. Organizing records should not delay veterinary care.

## Shareable pet-life summaries

The base `petlife.py build` returns budget and handoff documents. A playful “猫老板财务审计” voice can wrap verified figures, but keep unknowns visible. For images, use only available host rendering tools; the Skill doesn't require a graphics package. Public/shareable outputs need synthetic or explicitly approved redacted data. Original receipts, contact information and clinical records stay local by default; sending a report to someone else requires the user's instruction.
