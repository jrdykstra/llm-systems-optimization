"""Shared utility functions."""

import json
import sys
from pathlib import Path


def load_jsonl(path, keyed_by_id=False):
    """
    Parse a JSONL file.

    If keyed_by_id=False (default): returns list of dicts.
    If keyed_by_id=True: returns dict of id -> row.
    """
    rows = []
    path = Path(path)

    with open(path, encoding="utf-8") as f:
        for lineno, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                print(f"FAIL: {path}:{lineno} — invalid JSON: {exc}", file=sys.stderr)
                sys.exit(1)
            rows.append(obj)

    if keyed_by_id:
        return {r["id"]: r for r in rows}

    return rows
