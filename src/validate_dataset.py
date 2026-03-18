"""Validate router_v1 dataset files (tasks.jsonl + gold.jsonl)."""

import json
import sys
from pathlib import Path

from src.schema.extraction import (
    TASKS_KEYS, GOLD_KEYS, VALID_ENTITY_TYPES,
    VALID_ACTION_TYPES, VALID_JURISDICTIONS,
)

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


def validate_tasks(rows):
    """Validate every task row and return list of ids."""
    ids = []
    for lineno, obj in rows:
        label = f"tasks.jsonl:{lineno}"
        check_keys(obj, TASKS_KEYS, label)
        ids.append(obj["id"])
        if obj["task_type"] != "extraction_v1":
            fail(f'{label}: task_type must be "extraction_v1", '
                 f'got "{obj["task_type"]}"')
    return ids


def validate_gold(rows):
    """Validate every gold row and return list of ids."""
    ids = []
    for lineno, obj in rows:
        label = f"gold.jsonl:{lineno}"
        check_keys(obj, GOLD_KEYS, label)
        ids.append(obj["id"])
        validate_enums(obj, label)
    return ids


def validate_enums(exp, label):
    """Check that enum fields contain allowed values."""
    pet = exp["primary_entity_type"]
    if pet not in VALID_ENTITY_TYPES:
        fail(f"{label}: primary_entity_type '{pet}' not in {VALID_ENTITY_TYPES}")

    at = exp["action_type"]
    if at not in VALID_ACTION_TYPES:
        fail(f"{label}: action_type '{at}' not in {VALID_ACTION_TYPES}")

    jur = exp["jurisdiction"]
    if jur is not None and jur not in VALID_JURISDICTIONS:
        fail(f"{label}: jurisdiction '{jur}' not in {VALID_JURISDICTIONS} ∪ {{null}}")


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
    base = Path(__file__).resolve().parent.parent / "datasets" / "router_v1"
    tasks_path = base / "tasks.jsonl"
    gold_path = base / "gold.jsonl"

    task_rows = load_jsonl(tasks_path)
    gold_rows = load_jsonl(gold_path)

    task_ids = validate_tasks(task_rows)
    gold_ids = validate_gold(gold_rows)

    check_ids_unique(task_ids, "tasks.jsonl")
    check_ids_unique(gold_ids, "gold.jsonl")
    check_ids_match(task_ids, gold_ids)

    print(f"OK — {len(task_rows)} tasks, {len(gold_rows)} gold labels, "
          f"all ids aligned.")


if __name__ == "__main__":
    main()
