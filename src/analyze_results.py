"""Per-field and difficulty-stratified analysis of graded runs."""

import json
import argparse
from pathlib import Path
from collections import defaultdict


def load_jsonl(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def per_field_breakdown(grades, label):
    """Print per-field accuracy for one run."""
    fields = [
        "primary_entity", "primary_entity_type", "secondary_entity",
        "action_type", "amount_usd", "date", "jurisdiction",
    ]

    n = sum(1 for r in grades if r["schema_valid"])
    if n == 0:
        print(f"\n=== {label}: no schema-valid predictions ===")
        return

    print(f"\n=== {label} per-field accuracy ({n} schema-valid) ===")
    print(f"{'Field':25s}  {'Correct':>7s}  {'Rate':>6s}")
    print("-" * 42)

    for field in fields:
        correct = sum(
            1 for r in grades
            if r["schema_valid"] and r["field_correct"].get(field, False)
        )
        print(f"{field:25s}  {correct:>4d}/{n:<3d}  {correct/n:.1%}")


def difficulty_breakdown(grades, tasks, label):
    """Print accuracy stratified by task difficulty."""
    diff_by_id = {t["id"]: t["difficulty"] for t in tasks}

    buckets = defaultdict(list)
    for r in grades:
        diff = diff_by_id.get(r["id"], "unknown")
        buckets[diff].append(r)

    print(f"\n=== {label} by difficulty ===")
    print(f"{'Difficulty':12s}  {'N':>3s}  {'Perfect':>7s}  {'Mean':>6s}")
    print("-" * 34)

    for diff in ["easy", "medium", "hard"]:
        rows = buckets.get(diff, [])
        if not rows:
            continue
        n = len(rows)
        perfect = sum(1 for r in rows if r["total_score"] >= 1.0 - 1e-9)
        mean = sum(r["total_score"] for r in rows) / n
        print(f"{diff:12s}  {n:>3d}  {perfect:>4d}/{n:<3d}  {mean:.4f}")


def main():
    parser = argparse.ArgumentParser(description="Per-field and difficulty analysis.")
    parser.add_argument("grade_files", nargs="+", help="One or more *_grades.jsonl files.")
    parser.add_argument(
        "--tasks",
        default="datasets/router_v1/tasks.jsonl",
        help="Path to tasks.jsonl for difficulty labels.",
    )
    args = parser.parse_args()

    tasks = load_jsonl(Path(args.tasks))

    for path_str in args.grade_files:
        path = Path(path_str)
        grades = load_jsonl(path)
        label = path.stem
        per_field_breakdown(grades, label)
        difficulty_breakdown(grades, tasks, label)


if __name__ == "__main__":
    main()
