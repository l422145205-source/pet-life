# Compact household record

All examples are synthetic. Monetary amounts use decimal-compatible numbers or numeric strings; one file uses one currency. Python's `Decimal` handles calculations.

For optional batch counts, caregiver tasks, observations and safe append updates, see [everyday-workflows.md](everyday-workflows.md). Existing base records continue to work without those fields.

| Field | Meaning |
| --- | --- |
| `currency` | Explicit currency code, e.g. `CNY`; never guessed |
| `pets[]` | Unique `id`, nickname `name`, `species` (`cat` or `dog`), optional `routine` strings, optional `care_source` |
| `products[]` | Unique `id`, `name`, `base_unit` (`g`, `ml`, `piece`), optional positive `pack_size` in base units, optional `pack_label`, optional `category` |
| `products[].calories` | Optional `{kcal, per_quantity, unit, source}` from a label; e.g. 3800 kcal per 1 kg |
| `inventory[]` | One end-of-day snapshot per product: `product_id`, `quantity`, `unit`, `as_of`, `source` |
| `daily_plan[]` | One line per pet/product: `pet_id`, `product_id`, positive `quantity`, `unit`, `source`; the owner's supplied existing daily quantities |
| `records[]` | Stable unique `id`, `date`, `kind`, `source`, and type-specific fields below |
| `handoff` | Optional `feeding_times`, `separation`, `emergency_plan` strings supplied by the owner; private contacts stay local |

Record kinds:

- `purchase`: `product_id`, `quantity`, `unit`, optional non-negative `paid`. Missing paid is unknown, not free. Optional currency must equal the household currency.
- `use`: `product_id`, `quantity`, `unit`, optional `pet_id`.
- `expense`: non-negative `paid`, `category`; services or an unallocated order total. Do not also count that order's paid total in its individual purchase lines.
- `note`: `pet_id`, `text`; owner observations, not inferred diagnoses. A note does not change stock or spending.

Every record requires a compact `source` ID, not a path. Identical records with the same ID are ignored after their first occurrence. The same ID with different contents raises an error for reconciliation. Separate purchases with identical totals still need distinct IDs. Use receipt ID plus line number where available. An uncertain OCR record can carry `confirmed:false`; the helper skips it and reports it for review.

## Unit and date rules

Allowed units: `g`, `kg`, `ml`, `l`, `piece`, `pack`. A pack converts only with explicit product `pack_size`. A cup, scoop, bag, can or box must first be normalized using a supplied measure; a missing size stays unresolved. `base_unit:g` cannot consume ml. Commas, units embedded in numbers, booleans, NaN and infinity are rejected rather than silently parsed.

Inventory snapshots represent the end of their stated date, so movements **on or before** that date are already included and must not be added again. Only later movements through `--as-of` affect book stock. No initial count means unknown stock, even if a receipt exists. A negative balance signals missing/wrong records; no coverage forecast is emitted. A snapshot dated after `--as-of` is not used.

Spending includes the chosen period inclusively. Future records are excluded. A last-purchase unit price can predate the spending period and is labeled a projection, not actual consumption spending. Products with missing prices are excluded from projections, never called free. Plan calories and appropriate medical calorie targets are different concepts; only calories implied by supplied daily quantities are calculated.

`--trip-days` multiplies per-pet daily quantities for packing. Missing times or contacts remain gaps. Duplicate daily-plan rows for a pet/product are rejected; combine an explicitly confirmed total before running.

## Minimal example

```json
{
  "currency":"CNY",
  "pets":[{"id":"cat-1","name":"Mochi","species":"cat"}],
  "products":[{"id":"dry","name":"Example kibble","base_unit":"g","pack_size":2000}],
  "inventory":[{"product_id":"dry","quantity":600,"unit":"g","as_of":"2026-10-01","source":"S1"}],
  "daily_plan":[{"pet_id":"cat-1","product_id":"dry","quantity":60,"unit":"g","source":"Owner's existing routine"}],
  "records":[{"id":"R1-1","date":"2026-10-01","kind":"purchase","product_id":"dry","quantity":1,"unit":"pack","paid":120,"source":"R1 line 1"}]
}
```

With `--as-of 2026-10-01`: 600 g stock, 10 days of coverage, receipt unit price CNY 0.06/g. The purchase's 2000 g is not added to a same-day end-of-day snapshot.
