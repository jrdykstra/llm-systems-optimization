"""
Grade a predictions JSONL file against router_v1 gold labels.

Expected prediction row format (minimum):
    {"id": "task_001", "output_text": "..."}

Optional extra fields are preserved if present, for example:
    {"id": "task_001", "output_text": "...", "model": "gpt-4o-mini", "prompt_version": "v1"}

Usage:
    python src/grade_predictions.py --predictions runs/predictions.jsonl
    python src/grade_predictions.py --predictions runs/predictions.jsonl --output runs/grades.jsonl

Behavior:
- Fails fast on malformed JSONL
- Fails if prediction ids are duplicated
- Fails if a prediction id is not present in gold.jsonl
- Grades each prediction deterministically with src.grading.grade_extraction
- Writes one graded JSON object per line
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

from src.grading import grade_extraction

JsonDict = Dict[str, Any]


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def load_jsonl(path: Path) -> List[Tuple[int, JsonDict]]:
    """
    Parse a JSONL file and return list of (line_number, obj).
    Fails fast on invalid JSON or non-object rows.
    """
    rows: List[Tuple[int, JsonDict]] = []

    if not path.exists():
        fail(f"file not found: {path}")

    with path.open(encoding="utf-8") as f:
        for lineno, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line:
                continue

            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                fail(f"{path}:{lineno}: invalid JSON: {exc}")

            if not isinstance(obj, dict):
                fail(f"{path}:{lineno}: each JSONL row must be a JSON object")

            rows.append((lineno, obj))

    return rows


def build_gold_by_id(gold_rows: List[Tuple[int, JsonDict]]) -> Dict[str, JsonDict]:
    """
    Build id -> gold row map.
    Fails on missing id or duplicate ids.
    """
    gold_by_id: Dict[str, JsonDict] = {}

    for lineno, obj in gold_rows:
        label = f"gold.jsonl:{lineno}"

        if "id" not in obj:
            fail(f"{label}: missing required key 'id'")
        if not isinstance(obj["id"], str):
            fail(f"{label}: id must be a string")

        row_id = obj["id"]
        if row_id in gold_by_id:
            fail(f"{label}: duplicate gold id '{row_id}'")

        gold_by_id[row_id] = obj

    return gold_by_id


def validate_prediction_rows(pred_rows: List[Tuple[int, JsonDict]], gold_by_id: Dict[str, JsonDict]) -> None:
    """
    Validate predictions file structure:
    - each row has string id
    - each row has string output_text
    - no duplicate ids
    - every id exists in gold
    """
    seen_ids = set()

    for lineno, obj in pred_rows:
        label = f"predictions.jsonl:{lineno}"

        if "id" not in obj:
            fail(f"{label}: missing required key 'id'")
        if "output_text" not in obj:
            fail(f"{label}: missing required key 'output_text'")

        if not isinstance(obj["id"], str):
            fail(f"{label}: id must be a string")
        if not isinstance(obj["output_text"], str):
            fail(f"{label}: output_text must be a string")

        row_id = obj["id"]

        if row_id in seen_ids:
            fail(f"{label}: duplicate prediction id '{row_id}'")
        seen_ids.add(row_id)

        if row_id not in gold_by_id:
            fail(f"{label}: prediction id '{row_id}' not found in gold.jsonl")


def grade_rows(
    pred_rows: List[Tuple[int, JsonDict]],
    gold_by_id: Dict[str, JsonDict],
) -> List[JsonDict]:
    """
    Grade all prediction rows and return graded result rows.
    Preserves selected metadata fields if present.
    """
    graded: List[JsonDict] = []

    for _, pred_row in pred_rows:
        row_id = pred_row["id"]
        output_text = pred_row["output_text"]
        gold_obj = gold_by_id[row_id]

        grade = grade_extraction(output_text, gold_obj)

        out_row: JsonDict = {
            "id": row_id,
            "gold_id": grade["gold_id"],
            "valid_json": grade["valid_json"],
            "schema_valid": grade["schema_valid"],
            "base_score": grade["base_score"],
            "field_correct": grade["field_correct"],
            "field_scores": grade["field_scores"],
            "total_score": grade["total_score"],
            "errors": grade["errors"],
        }

        # Preserve useful metadata if present
        for key in (
            "model",
            "prompt_version",
            "latency_ms",
            "input_tokens",
            "output_tokens",
            "cost_usd",
        ):
            if key in pred_row:
                out_row[key] = pred_row[key]

        graded.append(out_row)

    return graded


def write_jsonl(path: Path, rows: List[JsonDict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def summarize(rows: List[JsonDict]) -> None:
    n = len(rows)
    if n == 0:
        print("OK: 0 predictions graded.")
        return

    mean_score = sum(float(r["total_score"]) for r in rows) / n
    perfect = sum(1 for r in rows if float(r["total_score"]) == 1.0)
    valid_json = sum(1 for r in rows if r["valid_json"] is True)
    schema_valid = sum(1 for r in rows if r["schema_valid"] is True)

    print(
        f"OK: graded {n} predictions | "
        f"mean_score={mean_score:.4f} | "
        f"perfect={perfect}/{n} | "
        f"valid_json={valid_json}/{n} | "
        f"schema_valid={schema_valid}/{n}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Grade predictions JSONL against router_v1 gold labels.")
    parser.add_argument(
        "--predictions",
        required=True,
        help="Path to predictions JSONL file.",
    )
    parser.add_argument(
        "--gold",
        default="datasets/router_v1/gold.jsonl",
        help="Path to gold JSONL file. Default: datasets/router_v1/gold.jsonl",
    )
    parser.add_argument(
        "--output",
        default="runs/grades.jsonl",
        help="Path to output grades JSONL. Default: runs/grades.jsonl",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    predictions_path = Path(args.predictions)
    gold_path = Path(args.gold)
    output_path = Path(args.output)

    gold_rows = load_jsonl(gold_path)
    gold_by_id = build_gold_by_id(gold_rows)

    pred_rows = load_jsonl(predictions_path)
    validate_prediction_rows(pred_rows, gold_by_id)

    graded_rows = grade_rows(pred_rows, gold_by_id)
    write_jsonl(output_path, graded_rows)
    summarize(graded_rows)


if __name__ == "__main__":
    main()