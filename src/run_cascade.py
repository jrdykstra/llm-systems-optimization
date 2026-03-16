"""Cascade router: run cheap model first,
 escalate to expensive model on failure."""

import json
import argparse
from pathlib import Path

from src.models.openai_model import OpenAIModel
from src.grading import parse_pred_object, validate_schema


DATASET_PATH = Path("datasets/router_v1/tasks.jsonl")
RUNS_DIR = Path("runs")


def load_tasks(path):
    tasks = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            tasks.append(json.loads(line))
    return tasks


def build_prompt(task: dict) -> str:
    input_text = task["input"].strip()

    return f"""Extract structured data from the input text and return a single JSON object. No markdown, no explanation — raw JSON only.

    Field rules:
    - primary_entity: string — the main subject (see role rules below)
    - primary_entity_type: one of exactly: company | agency | individual
    - secondary_entity: string or null
    - action_type: one of exactly: acquisition | fine | lawsuit | partnership | investigation
    - amount_usd: number (integer) or null — convert "$1.2 billion" -> 1200000000, "$520 million" -> 520000000.
        If the amount is in a non-USD currency (e.g. €, £), use null.
    - date: string in YYYY-MM-DD format or null — "December 2022" -> "2022-12-01", "in 2023" -> "2023-01-01"
    - jurisdiction: one of exactly: US | EU | UK | Other | null
        Only infer jurisdiction from this exact list of regulators:
            FTC → US, SEC → US, European Commission → EU,
            UK Financial Conduct Authority → UK, UK Competition and Markets Authority → UK,
            Japan's Fair Trade Commission → Other.
        If the regulator is not in this list and no explicit location is stated, use null.

    Role rules (which entity is primary vs secondary):
    - acquisition: primary = acquirer, secondary = target
    - fine: primary = entity fined, secondary = entity imposing fine
    - lawsuit: primary = plaintiff/filer, secondary = defendant
    - partnership: primary = first-named entity, secondary = second-named entity
    - investigation: primary = entity under investigation, secondary = investigating body

    Input: {input_text}"""


def should_escalate(output_text):
    """Return True if the cheap model output fails parse, schema, or semantic heuristics."""
    pred_obj, parse_errors = parse_pred_object(output_text, allow_embedded_json=True)
    if pred_obj is None:
        return True, parse_errors

    schema_errors = validate_schema(pred_obj)
    if schema_errors:
        return True, schema_errors

    # Semantic heuristic: in lawsuits, mini consistently puts the defendant as primary instead of the plaintiff.
    # If action is lawsuit and primary is a company, the model likely swapped roles, 
    # agencies/individuals are the usual filers.
    if (pred_obj.get("action_type") == "lawsuit"
            and pred_obj.get("primary_entity_type") == "company"):
        return True, ["heuristic:lawsuit_role_swap"]

    # Semantic heuristic: jurisdiction "Other" is rarely correct
    # models guess "Other" for unlisted regulators instead of null.
    if pred_obj.get("jurisdiction") == "Other":
        return True, ["heuristic:jurisdiction_other"]

    return False, []



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cheap", default="gpt-4o-mini", help="Cheap model name")
    parser.add_argument("--expensive", default="gpt-4o", help="Expensive model name")
    args = parser.parse_args()

    tasks = load_tasks(DATASET_PATH)

    cheap_model = OpenAIModel(args.cheap)
    expensive_model = OpenAIModel(args.expensive)

    output_path = RUNS_DIR / f"cascade_{args.cheap}_{args.expensive}_predictions.jsonl"

    escalated_count = 0

    with open(output_path, "w", encoding="utf-8") as out:
        for i, task in enumerate(tasks, start=1):
            prompt = build_prompt(task)

            # Step 1: try cheap model
            cheap_result = cheap_model.generate(prompt)
            escalate, reasons = should_escalate(cheap_result.output_text)

            if escalate:
                # Step 2: escalate to expensive model
                escalated_count += 1
                print(f"[{i}/{len(tasks)}] {task['id']} — ESCALATED ({reasons})")
                exp_result = expensive_model.generate(prompt)

                row = {
                    "id": task["id"],
                    "model": args.expensive,
                    "routed_from": args.cheap,
                    "escalated": True,
                    "escalation_reasons": reasons,
                    "prompt_version": "v1",
                    "output_text": exp_result.output_text,
                    "latency_ms": cheap_result.latency_ms + exp_result.latency_ms,
                    "input_tokens": (cheap_result.input_tokens or 0) + (exp_result.input_tokens or 0),
                    "output_tokens": (cheap_result.output_tokens or 0) + (exp_result.output_tokens or 0),
                    "cost_usd": (cheap_result.cost_usd or 0) + (exp_result.cost_usd or 0),
                }
            else:
                print(f"[{i}/{len(tasks)}] {task['id']} — accepted (cheap)")
                row = {
                    "id": task["id"],
                    "model": args.cheap,
                    "routed_from": None,
                    "escalated": False,
                    "escalation_reasons": [],
                    "prompt_version": "v2",
                    "output_text": cheap_result.output_text,
                    "latency_ms": cheap_result.latency_ms,
                    "input_tokens": cheap_result.input_tokens,
                    "output_tokens": cheap_result.output_tokens,
                    "cost_usd": cheap_result.cost_usd,
                }

            out.write(json.dumps(row) + "\n")

    print(f"\nDone. {escalated_count}/{len(tasks)} escalated.")
    print(f"Predictions written to {output_path}")


if __name__ == "__main__":
    main()
