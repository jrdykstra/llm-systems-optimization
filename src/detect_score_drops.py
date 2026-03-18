"""Compare two grade files and flag tasks that got worse."""

import json
import argparse
from pathlib import Path
from src.utils import load_jsonl

def detect(before, after, threshold=0.0):
    """
    Compare two grade dicts by task id.
    Returns list of regressions where score dropped by more than threshold.
    """
    regressions = []
    for task_id in sorted(before.keys()):
        if task_id not in after:
            continue
        score_before = before[task_id]["total_score"]
        score_after = after[task_id]["total_score"]
        delta = score_after - score_before

        if delta < -threshold:
            regressions.append({
                "id": task_id,
                "before": score_before,
                "after": score_after,
                "delta": delta,
                "errors_before": before[task_id].get("errors", []),
                "errors_after": after[task_id].get("errors", []),
            })

    return regressions


def print_report(regressions, label_before, label_after):
    """Print regression report."""
    if not regressions:
        print(f"No regressions: {label_before} → {label_after}")
        return

    print(f"\n=== Regressions: {label_before} → {label_after} ({len(regressions)} found) ===\n")
    print(f"{'ID':8s}  {'Before':>6s}  {'After':>6s}  {'Delta':>6s}  Errors (after)")
    print("-" * 70)

    for r in regressions:
        errors = ", ".join(r["errors_after"]) if r["errors_after"] else "none"
        print(f"{r['id']:8s}  {r['before']:6.2f}  {r['after']:6.2f}  {r['delta']:+6.2f}  {errors}")

    total_lost = sum(r["delta"] for r in regressions)
    print(f"\nTotal score lost: {total_lost:+.2f} across {len(regressions)} tasks")


def main():
    parser = argparse.ArgumentParser(description="Detect score regressions between two runs.")
    parser.add_argument("before", help="Baseline grades JSONL (the 'good' run).")
    parser.add_argument("after", help="New grades JSONL (the run to check).")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.0,
        help="Minimum score drop to flag (default 0.0 = any drop).",
    )
    args = parser.parse_args()

    before = load_jsonl(args.before, keyed_by_id=True)
    after = load_jsonl(args.after, keyed_by_id=True)

    label_before = Path(args.before).stem.replace("_grades", "")
    label_after = Path(args.after).stem.replace("_grades", "")

    regressions = detect(before, after, args.threshold)
    print_report(regressions, label_before, label_after)


if __name__ == "__main__":
    main()
