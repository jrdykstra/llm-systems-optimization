"""Cascade router: run cheap model first,
 escalate to expensive model on failure."""

import json
import argparse
from pathlib import Path

from src.models.openai_model import OpenAIModel
from src.grading import parse_pred_object, validate_schema, validate_antitrust_schema

from src.schema.extraction import KNOWN_REGULATORS

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


def build_prompt(task, prompt_path) -> str:
    template = prompt_path.read_text(encoding="utf-8")
    return template.replace("{input}", task["input"].strip())

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
        secondary = pred_obj.get("secondary_entity", "")
        if secondary not in KNOWN_REGULATORS:
            return True, ["heuristic:jurisdiction_other_unknown_regulator"]
        
    return False, []

def should_escalate_antitrust(output_text):
    """Return True if the cheap model output fails parse, schema, or antitrust heuristics."""
    pred_obj, parse_errors = parse_pred_object(output_text, allow_embedded_json=True)
    if pred_obj is None:
        return True, parse_errors

    schema_errors = validate_antitrust_schema(pred_obj)
    if schema_errors:
        return True, schema_errors

    # Heuristic: plaintiff/defendant swap — if plaintiff looks like a person/company
    # and defendant looks like a government entity, they're probably swapped
    plaintiff = (pred_obj.get("plaintiff") or "").lower()
    gov_keywords = ["doj", "department of justice", "united states", "ftc", "federal trade"]
    if not any(kw in plaintiff for kw in gov_keywords):
        return True, ["heuristic:plaintiff_not_government"]

    return False, []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cheap", default="gpt-4o-mini", help="Cheap model name")
    parser.add_argument("--expensive", default="gpt-4o", help="Expensive model name")
    parser.add_argument("--task-type", default="extraction_v1",
                        choices=["extraction_v1", "antitrust_v1"])
    args = parser.parse_args()

    dataset_path = Path(f"datasets/{args.task_type}/tasks.jsonl")
    prompt_path = Path(f"prompts/{args.task_type.split('_')[0]}.txt")

    tasks = load_tasks(dataset_path)

    cheap_model = OpenAIModel(args.cheap)
    expensive_model = OpenAIModel(args.expensive)
    escalate_fn = should_escalate_antitrust if args.task_type == "antitrust_v1" else should_escalate

    output_path = RUNS_DIR / f"cascade_{args.cheap}_{args.expensive}_{args.task_type}_predictions.jsonl"

    escalated_count = 0

    with open(output_path, "w", encoding="utf-8") as out:
        for i, task in enumerate(tasks, start=1):
            prompt = build_prompt(task, prompt_path)

            # Step 1: try cheap model
            cheap_result = cheap_model.generate(prompt)
            escalate, reasons = escalate_fn(cheap_result.output_text)

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
                    "prompt_version": args.task_type,
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
                    "prompt_version": args.task_type,
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
