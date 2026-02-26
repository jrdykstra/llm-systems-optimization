# extraction_v1 — Schema Specification

Task type identifier: `extraction_v1`

## Output Schema

The model must return a single JSON object with exactly these fields:

| Field                | Type                                                        | Required |
|----------------------|-------------------------------------------------------------|----------|
| primary_entity       | string                                                      | yes      |
| primary_entity_type  | enum: `company` \| `agency` \| `individual`                 | yes      |
| secondary_entity     | string \| null                                              | yes      |
| action_type          | enum: `acquisition` \| `fine` \| `lawsuit` \| `partnership` \| `investigation` | yes |
| amount_usd           | number \| null                                              | yes      |
| date                 | string (YYYY-MM-DD) \| null                                 | yes      |
| jurisdiction         | enum: `US` \| `EU` \| `UK` \| `Other` \| null              | yes      |

All seven fields must be present in every response. No additional fields are allowed.

## Entity Role Definitions

Which entity is primary vs secondary depends on `action_type`:

| action_type    | primary_entity               | secondary_entity              |
|----------------|------------------------------|-------------------------------|
| acquisition    | acquirer                     | target                        |
| fine           | entity fined                 | entity imposing the fine      |
| lawsuit        | plaintiff / filer            | defendant                     |
| partnership    | first-named entity in input  | second-named entity in input  |
| investigation  | entity under investigation   | investigating body            |

## Normalization Rules

### Dates

- Full date (e.g. "April 24, 2024") → `"2024-04-24"`
- Month + year (e.g. "December 2022") → first day of that month → `"2022-12-01"`
- Year only (e.g. "in 2023") → January 1 of that year → `"2023-01-01"`
- Not mentioned → `null`

### Monetary Amounts

Convert English money strings to numeric USD:

- "$700 million" → `700000000`
- "$1.2 billion" → `1200000000`
- "$61.6 million" → `61600000`
- "$15 million" → `15000000`
- Not mentioned → `null`

All amounts are assumed USD. Currency conversion is out of scope for v1.

### Jurisdiction

Jurisdiction inference from regulator names is restricted to the explicit mapping
table below. Any regulator not in this table does **not** imply a jurisdiction.

| Regulator name                        | Jurisdiction |
|---------------------------------------|--------------|
| FTC                                   | `"US"`       |
| SEC                                   | `"US"`       |
| European Commission                   | `"EU"`       |
| UK Financial Conduct Authority        | `"UK"`       |
| UK Competition and Markets Authority  | `"UK"`       |
| Japan's Fair Trade Commission         | `"Other"`    |

Resolution order:

1. If a regulator from the table above appears → use the mapped value.
2. Else if an explicit location is stated (e.g. "in the United States") → use that.
3. Otherwise → `null`.

### Entity Names

Use the surface form as it appears in the input text. Do not expand abbreviations
(e.g. keep "FTC", not "Federal Trade Commission" unless the input uses the full name).

## Grading Rules (Week 1)

### Step 1 — Validity gate

If the response is **not valid JSON** or does **not conform** to the schema above
(missing fields, extra fields, wrong enum values, wrong types), the score is **0.00**.
No partial credit.

### Step 2 — Base score

A schema-valid response receives a base score of **0.30**.

### Step 3 — Per-field scoring

Each field is compared to the gold label. A correct field adds its weight to the score.
An incorrect field adds nothing.

| Field                | Weight |
|----------------------|--------|
| primary_entity       | 0.15   |
| primary_entity_type  | 0.05   |
| secondary_entity     | 0.10   |
| action_type          | 0.10   |
| amount_usd           | 0.10   |
| date                 | 0.10   |
| jurisdiction         | 0.10   |
| **Total per-field**  | **0.70** |

**Maximum score** = 0.30 (base) + 0.70 (all fields correct) = **1.00**

### Field Comparison Rules

| Type          | Rule                                                        |
|---------------|-------------------------------------------------------------|
| string        | Case-insensitive exact match                                |
| enum          | Exact match (enums are lowercase by definition)             |
| number        | Both null → match. Both numeric and `abs(pred - gold) ≤ 1e-6` → match. Otherwise mismatch. |
| date (string) | Exact string match after normalization to YYYY-MM-DD        |
| null          | Both predicted and gold must be null; mismatch scores 0     |
