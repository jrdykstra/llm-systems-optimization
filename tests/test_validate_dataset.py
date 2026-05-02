import json
import pytest
from pathlib import Path

from src.validate_dataset import (
    load_jsonl, check_keys, validate_tasks, validate_gold,
    check_ids_unique, check_ids_match,
)
from src.schema.extraction import TASKS_KEYS, GOLD_KEYS


def test_load_valid_jsonl(tmp_path):
    f = tmp_path / "test.jsonl"
    f.write_text('{"id": "1"}\n{"id": "2"}\n')
    rows = load_jsonl(f)
    assert len(rows) == 2


def test_load_skips_blank_lines(tmp_path):
    f = tmp_path / "test.jsonl"
    f.write_text('{"id": "1"}\n\n{"id": "2"}\n')
    rows = load_jsonl(f)
    assert len(rows) == 2


def test_check_keys_exact_passes():
    obj = {"id": "1", "task_type": "extraction_v1", "difficulty": "easy",
           "input": "text", "instruction": "do it"}
    # Should not raise
    check_keys(obj, TASKS_KEYS, "test")


def test_validate_tasks_returns_ids():
    rows = [
        (1, {"id": "A0001", "task_type": "extraction_v1", "difficulty": "easy",
             "input": "text", "instruction": "do it"}),
    ]
    ids = validate_tasks(rows, TASKS_KEYS, "extraction_v1")
    assert ids == ["A0001"]


def test_check_ids_unique_passes():
    check_ids_unique(["A0001", "A0002", "A0003"], "test.jsonl")


def test_check_ids_match_passes():
    check_ids_match(["A0001", "A0002"], ["A0001", "A0002"])


def test_full_dataset_validates():
    """Integration test: actual dataset files pass validation."""
    base = Path(__file__).resolve().parent.parent / "datasets" / "extraction_v1"
    tasks = load_jsonl(base / "tasks.jsonl")
    gold = load_jsonl(base / "gold.jsonl")
    assert len(tasks) == len(gold)
    assert len(tasks) >= 30


def test_antitrust_dataset_validates():
    """Integration test: antitrust_v1 dataset files pass validation."""
    base = Path(__file__).resolve().parent.parent / "datasets" / "antitrust_v1"
    tasks = load_jsonl(base / "tasks.jsonl")
    gold = load_jsonl(base / "gold.jsonl")
    assert len(tasks) == len(gold)
    assert len(tasks) >= 10
