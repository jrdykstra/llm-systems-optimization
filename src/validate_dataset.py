"""Validate dataset files (tasks.jsonl + gold.jsonl) for any task type."""

import json
import sys
import argparse
from pathlib import Path


def load_schema(task_type):
    """Load the right schema constants for the task type."""
    if task_type == "extraction_v1":
        from src.schema.extraction import (
            TASKS_KEYS, GOLD_KEYS, VALID_ENTITY_TYPES,
            VALID_ACTION_TYPES, VALID_JURISDICTIONS,
        )
        enums = {
            "primary_entity_type": VALID_ENTITY_TYPES,
            "action_type": VALID_ACTION_TYPES,
            "jurisdiction": VALID_JURISDICTIONS,
        }
        return TASKS_KEYS, GOLD_KEYS, enums, task_type

    elif task_type == "antitrust_v1":
        from src.schema.antitrust import (
            TASKS_KEYS, GOLD_KEYS, VALID_CAUSES,
            VALID_REMEDIES, VALID_HOLDINGS,
        )
        enums = {
            "cause_of_action": VALID_CAUSES,
            "remedy_sought": VALID_REMEDIES,
            "holding": VALID_HOLDINGS,
        }
        return TASKS_KEYS, GOLD_KEYS, enums, task_type

    else:
        fail(f"Unknown task type: {task_type}")


def load_jsonl(path):
    """Parse a JSONL file. Returns list of (line_number, obj) tuples."""
    rows = []
    with open(path, encoding="utf-8") as f:
        for lineno, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                fail(f"{path}:{lineno} — invalid JSON: {exc}")
            rows.append((lineno, obj))
    return rows


def check_keys(obj, expected_keys, label):
    """Verify obj has exactly the expected keys."""
    actual = set(obj.keys())
    missing = expected_keys - actual
    extra = actual - expected_keys
    errors = []
    if missing:
        errors.append(f"missing keys {sorted(missing)}")
    if extra:
        errors.append(f"extra keys {sorted(extra)}")
    if errors:
        fail(f"{label}: {', '.join(errors)}")


def validate_tasks(rows, tasks_keys, expected_task_type):
    """Validate every task row and return list of ids."""
    ids = []
    for lineno, obj in rows:
        label = f"tasks.jsonl:{lineno}"
        check_keys(obj, tasks_keys, label)
        ids.append(obj["id"])
        if obj["task_type"] != expected_task_type:
            fail(f'{label}: task_type must be "{expected_task_type}", '
                 f'got "{obj["task_type"]}"')
    return ids


def validate_gold(rows, gold_keys, enums):
    """Validate every gold row and return list of ids."""
    ids = []
    for lineno, obj in rows:
        label = f"gold.jsonl:{lineno}"
        check_keys(obj, gold_keys, label)
        ids.append(obj["id"])
        validate_enums(obj, enums, label)
    return ids


def validate_enums(obj, enums, label):
    """Check that enum fields contain allowed values."""
    for field, valid_values in enums.items():
        val = obj[field]
        if val is not None and val not in valid_values:
            fail(f"{label}: {field} '{val}' not in {valid_values}")


def check_ids_unique(ids, filename):
    """Verify all ids are unique within a file."""
    seen = {}
    for idx, task_id in enumerate(ids, start=1):
        if task_id in seen:
            fail(f"{filename}: duplicate id '{task_id}' "
                 f"on lines {seen[task_id]} and {idx}")
        seen[task_id] = idx


def check_ids_match(task_ids, gold_ids):
    """Verify the two id sets match exactly."""
    task_set = set(task_ids)
    gold_set = set(gold_ids)
    only_tasks = task_set - gold_set
    only_gold = gold_set - task_set
    if only_tasks:
        fail(f"ids in tasks but not in gold: {sorted(only_tasks)}")
    if only_gold:
        fail(f"ids in gold but not in tasks: {sorted(only_gold)}")


def fail(msg):
    """Print error and exit."""
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Validate dataset files.")
    parser.add_argument(
        "--task-type",
        required=True,
        choices=["extraction_v1", "antitrust_v1"],
        help="Which schema to validate against.",
    )
    parser.add_argument(
        "--dataset-dir",
        default=None,
        help="Path to dataset directory. Defaults to datasets/<task_type>/",
    )
    args = parser.parse_args()

    tasks_keys, gold_keys, enums, task_type = load_schema(args.task_type)

    if args.dataset_dir:
        base = Path(args.dataset_dir)
    else:
        base = Path(__file__).resolve().parent.parent / "datasets" / args.task_type

    tasks_path = base / "tasks.jsonl"
    gold_path = base / "gold.jsonl"

    task_rows = load_jsonl(tasks_path)
    gold_rows = load_jsonl(gold_path)

    task_ids = validate_tasks(task_rows, tasks_keys, task_type)
    gold_ids = validate_gold(gold_rows, gold_keys, enums)

    check_ids_unique(task_ids, "tasks.jsonl")
    check_ids_unique(gold_ids, "gold.jsonl")
    check_ids_match(task_ids, gold_ids)

    print(f"OK — {len(task_rows)} tasks, {len(gold_rows)} gold labels, "
          f"all ids aligned ({task_type}).")


if __name__ == "__main__":
    main()
