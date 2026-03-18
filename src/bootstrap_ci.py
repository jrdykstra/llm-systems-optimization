"""Bootstrap confidence intervals for comparing strategy scores."""

import json
import random
import argparse
from pathlib import Path
from src.utils import load_jsonl

def bootstrap_mean_ci(scores, n_boot=100000, ci=95, seed=291281):
    """Compute bootstrap CI for mean score."""
    rng = random.Random(seed)
    vals = list(scores.values())
    n = len(vals)

    boot_means = []
    for _ in range(n_boot):
        sample = [rng.choice(vals) for _ in range(n)]
        boot_means.append(sum(sample) / n)

    boot_means.sort()
    lo_idx = int((100 - ci) / 2 / 100 * n_boot)
    hi_idx = int((100 + ci) / 2 / 100 * n_boot)

    return boot_means[lo_idx], boot_means[hi_idx]


def bootstrap_diff_ci(scores_a, scores_b, n_boot=100000, ci=95, seed=291281):
    """
    Compute bootstrap CI for the difference in means (B - A).
    Paired by task id — both must have the same ids.
    """
    rng = random.Random(seed)
    ids = sorted(scores_a.keys())
    diffs = [scores_b[i] - scores_a[i] for i in ids]
    n = len(diffs)

    boot_diffs = []
    for _ in range(n_boot):
        sample = [rng.choice(diffs) for _ in range(n)]
        boot_diffs.append(sum(sample) / n)

    boot_diffs.sort()
    lo_idx = int((100 - ci) / 2 / 100 * n_boot)
    hi_idx = int((100 + ci) / 2 / 100 * n_boot)

    return boot_diffs[lo_idx], boot_diffs[hi_idx]


def main():
    parser = argparse.ArgumentParser(description="Bootstrap CIs for strategy comparison.")
    parser.add_argument("grade_files", nargs="+", help="Two or more *_grades.jsonl files.")
    parser.add_argument("--n-boot", type=int, default=100000, help="Number of bootstrap samples.")
    parser.add_argument("--ci", type=int, default=95, help="Confidence level (default 95).")
    parser.add_argument("--seed", type=int, default=291281, help="Random seed.")
    args = parser.parse_args()

    runs = []
    for path_str in args.grade_files:
        path = Path(path_str)
        rows = load_jsonl(path_str)
        scores = {r["id"]: r["total_score"] for r in rows}
        label = path.stem.replace("_grades", "").replace("cascade_gpt-4o-mini_gpt-4o", "cascade")
        runs.append((label, scores))

    # Per-run CIs
    print(f"=== {args.ci}% Bootstrap CIs (n_boot={args.n_boot}) ===\n")
    print(f"{'Strategy':45s}  {'Mean':>6s}  {'CI Low':>7s}  {'CI High':>7s}")
    print("-" * 70)
    for label, scores in runs:
        mean = sum(scores.values()) / len(scores)
        lo, hi = bootstrap_mean_ci(scores, args.n_boot, args.ci, args.seed)
        print(f"{label:45s}  {mean:.4f}  {lo:.4f}   {hi:.4f}")

    # Pairwise diffs
    if len(runs) >= 2:
        print(f"\n=== Pairwise Differences (B - A) ===\n")
        print(f"{'Comparison':45s}  {'Diff':>6s}  {'CI Low':>7s}  {'CI High':>7s}  {'Significant':>11s}")
        print("-" * 80)
        for i in range(len(runs)):
            for j in range(i + 1, len(runs)):
                label_a, scores_a = runs[i]
                label_b, scores_b = runs[j]
                common = set(scores_a.keys()) & set(scores_b.keys())
                if not common:
                    continue
                sa = {k: scores_a[k] for k in common}
                sb = {k: scores_b[k] for k in common}
                diff = sum(sb.values()) / len(sb) - sum(sa.values()) / len(sa)
                lo, hi = bootstrap_diff_ci(sa, sb, args.n_boot, args.ci, args.seed)
                sig = "yes" if (lo > 0 or hi < 0) else "no"
                print(f"{label_a} vs {label_b:30s}  {diff:+.4f}  {lo:+.4f}  {hi:+.4f}  {sig:>11s}")


if __name__ == "__main__":
    main()
