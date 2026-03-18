"""Summarize one or more graded JSONL files into a comparison table."""

import json
import argparse
from pathlib import Path
from src.utils import load_jsonl


def summarize_one(rows):
    """Compute summary metrics for one run."""
    n = len(rows)
    if n == 0:
        return None

    mean_score = sum(r["total_score"] for r in rows) / n
    perfect = sum(1 for r in rows if r["total_score"] >= 1.0 - 1e-9)
    schema_valid = sum(1 for r in rows if r["schema_valid"])
    avg_latency = sum(r["latency_ms"] for r in rows) / n

    costs = [r["cost_usd"] for r in rows if r.get("cost_usd") is not None]
    total_cost = sum(costs) if costs else None

    cost_per_correct = None
    if total_cost is not None and perfect > 0:
        cost_per_correct = total_cost / perfect

    if any(r.get("escalated") for r in rows):
        model = "cascade"
    else:
        model = rows[0].get("model", "unknown")

    return {
        "model": model,
        "n": n,
        "mean_score": round(mean_score, 4),
        "perfect": perfect,
        "perfect_rate": round(perfect / n, 4),
        "schema_valid": schema_valid,
        "avg_latency_ms": round(avg_latency, 1),
        "total_cost_usd": round(total_cost, 6) if total_cost is not None else None,
        "cost_per_correct_usd": round(cost_per_correct, 6) if cost_per_correct is not None else None,
    }


def print_table(summaries):
    """Print a readable comparison table."""
    headers = ["Model", "N", "Mean", "Perfect", "Schema", "Avg Lat (ms)", "Total Cost", "Cost/Correct"]
    rows = []
    for s in summaries:
        cost = f"${s['total_cost_usd']:.6f}" if s["total_cost_usd"] is not None else "n/a"
        cpc = f"${s['cost_per_correct_usd']:.6f}" if s["cost_per_correct_usd"] is not None else "n/a"
        rows.append([
            s["model"],
            str(s["n"]),
            f"{s['mean_score']:.4f}",
            f"{s['perfect']}/{s['n']}",
            f"{s['schema_valid']}/{s['n']}",
            f"{s['avg_latency_ms']:.1f}",
            cost,
            cpc,
        ])

    # Compute column widths
    widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            widths[i] = max(widths[i], len(val))

    def fmt_row(vals):
        return " | ".join(v.rjust(widths[i]) for i, v in enumerate(vals))

    print(fmt_row(headers))
    print("-+-".join("-" * w for w in widths))
    for row in rows:
        print(fmt_row(row))


def main():
    parser = argparse.ArgumentParser(description="Summarize graded runs into a comparison table.")
    parser.add_argument(
        "grade_files",
        nargs="+",
        help="One or more *_grades.jsonl files to compare.",
    )
    args = parser.parse_args()

    summaries = []
    for path_str in args.grade_files:
        rows = load_jsonl(path_str)
        summary = summarize_one(rows)
        if summary:
            summaries.append(summary)

    print_table(summaries)


if __name__ == "__main__":
    main()
