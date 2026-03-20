# antitrust_v1 — Schema Specification

Task type identifier: `antitrust_v1`

## Output Schema

The model must return a single JSON object with exactly these fields:

| Field              | Type                                                              | Required |
|--------------------|-------------------------------------------------------------------|----------|
| case_name          | string                                                            | yes      |
| plaintiff          | string                                                            | yes      |
| defendant          | string                                                            | yes      |
| court              | string \| null                                                    | yes      |
| date_filed         | string (YYYY-MM-DD) \| null                                      | yes      |
| cause_of_action    | enum: `bid_rigging` \| `price_fixing` \| `monopolization` \| `merger_challenge` \| `wage_fixing` \| `algorithmic_pricing` | yes |
| statute            | string \| null                                                    | yes      |
| market_definition  | string \| null                                                    | yes      |
| remedy_sought      | enum: `criminal_penalty` \| `injunctive_relief` \| `divestiture` \| `consent_decree` \| `damages` \| null | yes |
| holding            | enum: `guilty_plea` \| `convicted` \| `settled` \| `dismissed` \| `pending` \| `approved` \| null | yes |

All ten fields must be present in every response. No additional fields are allowed.

## Field Definitions

- **case_name**: Official or descriptive case name (e.g. "United States v. Google")
- **plaintiff**: The party bringing the action (DOJ, FTC, state AG, etc.)
- **defendant**: The party being sued or investigated
- **court**: Full court name if mentioned, null otherwise
- **date_filed**: The date of the action described (filing, plea, sentencing). Normalize: month+year → first of month, year only → Jan 1
- **cause_of_action**: The primary antitrust violation alleged
- **statute**: The statute cited (e.g. "Sherman Act", "Clayton Act"), null if not mentioned
- **market_definition**: The relevant market as described in the case
- **remedy_sought**: What the government is seeking or obtained
- **holding**: The outcome or current status of the case

## Normalization Rules

### Dates
- Full date (e.g. "March 18, 2026") → `"2026-03-18"`
- Month + year (e.g. "December 2025") → `"2025-12-01"`
- Year only (e.g. "in 2025") → `"2025-01-01"`
- Not mentioned → `null`

### Entity Names
Use the surface form as it appears in the input text. Strip titles and honorifics.

## Grading Rules

### Step 1 — Validity gate
If the response is **not valid JSON** or does **not conform** to the schema above: score = **0.00**.

### Step 2 — Base score
A schema-valid response receives a base score of **0.20**.

### Step 3 — Per-field scoring

| Field              | Weight |
|--------------------|--------|
| case_name          | 0.05   |
| plaintiff          | 0.10   |
| defendant          | 0.10   |
| court              | 0.05   |
| date_filed         | 0.05   |
| cause_of_action    | 0.15   |
| statute            | 0.05   |
| market_definition  | 0.10   |
| remedy_sought      | 0.10   |
| holding            | 0.05   |
| **Total per-field**| **0.80** |

**Maximum score** = 0.20 (base) + 0.80 (all fields correct) = **1.00**

### Field Comparison Rules

| Type          | Rule                                                        |
|---------------|-------------------------------------------------------------|
| string        | Case-insensitive exact match                                |
| enum          | Exact match                                                 |
| number        | Both null → match. Both numeric and abs(pred-gold) ≤ 1e-6   |
| date (string) | Exact string match after normalization to YYYY-MM-DD        |
| null          | Both predicted and gold must be null; mismatch scores 0     |
