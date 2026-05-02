# LLM Systems Optimization

An empirical study of cost and accuracy tradeoffs in structured extraction with LLMs, plus a routing system built on those tradeoffs.

The project addresses one question: when does a cheaper model suffice for a structured extraction task, and when does it not. It evaluates `gpt-4o`, `gpt-4o-mini`, and a cascade router across two domains (general regulatory actions and DOJ antitrust cases) using a deterministic grading harness.

Full benchmark numbers: [results/RESULTS.md](results/RESULTS.md). Reproducible via `python scripts/generate_results.py`.

## Findings

1. On the regulatory extraction benchmark (50 tasks), `gpt-4o-mini` reaches 96% of `gpt-4o`'s mean score (0.942 vs 0.979) at roughly 6% of the cost.

2. On the antitrust benchmark (14 tasks), `gpt-4o-mini` exceeds `gpt-4o` (0.811 vs 0.700). The larger model emits schema-invalid JSON on 2/14 cases, which the deterministic grader scores as zero. The cheap model returns valid schemas on all 14. Output discipline, not raw capability, drives the gap.

3. A cascade that runs `gpt-4o-mini` first and escalates to `gpt-4o` on parse, schema, or semantic-heuristic failure improves mean score by 1 to 3 points over the cheap model alone, at 4 to 5 times the cheap-model cost. That is still 4 times cheaper than running `gpt-4o` on every input.

The cascade does not strictly dominate `gpt-4o` on every metric. It sits at a different point on the cost-accuracy frontier. The right choice depends on the budget and latency envelope of the deployment.

## Cascade design

The router in [src/run_cascade.py](src/run_cascade.py) escalates on three conditions:

1. JSON parse failure.
2. Schema validation failure (wrong keys, wrong types, invalid enum values).
3. Domain-specific semantic heuristics. For regulatory extraction, one heuristic flags lawsuits where the primary entity is a company, since the model frequently swaps plaintiff and defendant in that pattern. Another flags the jurisdiction value "Other" combined with an unrecognized regulator name.

Heuristics are designed from error analysis on prediction outputs, not learned. They target patterns with high false-negative cost and low false-positive risk. Escalation rate stayed low: 9/50 on regulatory extraction, 1/14 on antitrust.

## Datasets

Both datasets are JSONL with fixed schemas and gold labels. Grading is fully deterministic.

`extraction_v1` (50 tasks). Regulatory actions across acquisitions, fines, lawsuits, partnerships, and investigations. Seven fields per record. Difficulty splits drawn from real news coverage.

`antitrust_v1` (14 tasks). DOJ Antitrust Division press releases scraped with Selenium ([scripts/scrape_doj.py](scripts/scrape_doj.py)). Ten fields per record, with more free-text content (market definitions, holdings).

Per-field comparison rules are type-aware. Strings use case-insensitive exact match. Enums use exact match. Numbers use a fixed tolerance. Dates require exact YYYY-MM-DD match. Free-text fields like `market_definition` use a token-overlap (Jaccard) threshold to allow paraphrase. The grading contract is documented in [src/grading.py](src/grading.py).

## Components

```
src/models/             provider-agnostic model wrappers (OpenAI, HF, local)
src/schema/             task schema constants (keys, enums, weights)
src/grading.py          deterministic grader (parse, schema, field comparison)
src/run_model.py        single-model runner
src/run_cascade.py      cascade router with task-type heuristics
src/grade_predictions.py  batch grader, task-type aware
src/summarize_runs.py   comparison tables over graded JSONL files
scripts/scrape_doj.py   Selenium scraper for the antitrust dataset
scripts/generate_results.py  end-to-end benchmark runner
```

## Reproducing the results

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
echo OPENAI_API_KEY=sk-... > .env

python scripts/generate_results.py
```

Approximate cost: $0.10 in API spend, three minutes wall time. Existing prediction files are reused. Pass `--force` to re-run from scratch.

Single components:

```
python -m src.run_model --provider openai --model gpt-4o-mini --task-type antitrust_v1
python -m src.run_cascade --task-type antitrust_v1
python -m src.grade_predictions --predictions runs/<file>.jsonl --task-type antitrust_v1
```

## Tests

```
python -m pytest tests/ -v
```

33 tests covering grading edge cases, cascade heuristic logic, dataset structural validation, and pricing math.

## Scope and limits

The heuristics are hand-designed from error analysis on these specific datasets. The cost-accuracy frontier reported here is specific to the OpenAI `gpt-4o` family and these two extraction domains. Applying the same approach to other providers, model pairs, or tasks would require new heuristics and re-evaluation. The contribution is the methodology and the harness, not the specific routing rules.
