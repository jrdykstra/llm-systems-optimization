# tests/test_grading.py
from __future__ import annotations

import json

import pytest

from src.grading import (
    BASE_SCORE,
    EPS,
    FIELD_WEIGHTS,
    grade_extraction,
)


def _gold():
    # Matches extraction_v1 schema + gold includes id
    return {
        "id": "task_001",
        "primary_entity": "FTC",
        "primary_entity_type": "agency",
        "secondary_entity": "Amazon",
        "action_type": "lawsuit",
        "amount_usd": None,
        "date": "2023-01-01",
        "jurisdiction": "US",
    }


def _pred_obj_all_correct():
    g = _gold()
    g = dict(g)
    g.pop("id")
    return g


def test_invalid_no_json_object():
    res = grade_extraction("not json at all", _gold())
    assert res["valid_json"] is False
    assert res["schema_valid"] is False
    assert res["total_score"] == 0.0
    assert res["errors"] == ["no_json_object"]


def test_invalid_json_substring():
    # Has braces, but not valid JSON
    res = grade_extraction("prefix {bad json} suffix", _gold())
    assert res["valid_json"] is False
    assert res["schema_valid"] is False
    assert res["total_score"] == 0.0
    assert res["errors"] == ["invalid_json"]


def test_pred_not_object():
    # Valid JSON but not an object
    res = grade_extraction('["a", "b"]', _gold())
    assert res["valid_json"] is False
    assert res["schema_valid"] is False
    assert res["total_score"] == 0.0
    assert res["errors"] == ["pred_not_object"]


def test_schema_missing_keys_is_zero():
    pred = {"primary_entity": "FTC"}  # missing 6 required keys
    res = grade_extraction(json.dumps(pred), _gold())
    assert res["valid_json"] is True
    assert res["schema_valid"] is False
    assert res["total_score"] == 0.0
    assert res["errors"][0].startswith("missing_keys:")


def test_schema_extra_keys_is_zero():
    pred = _pred_obj_all_correct()
    pred["extra"] = 123
    res = grade_extraction(json.dumps(pred), _gold())
    assert res["valid_json"] is True
    assert res["schema_valid"] is False
    assert res["total_score"] == 0.0
    assert res["errors"][0].startswith("extra_keys:")


def test_schema_wrong_enum_is_zero():
    pred = _pred_obj_all_correct()
    pred["action_type"] = "merge"
    res = grade_extraction(json.dumps(pred), _gold())
    assert res["valid_json"] is True
    assert res["schema_valid"] is False
    assert res["total_score"] == 0.0
    assert res["errors"] == ["enum_error:action_type"]


def test_schema_wrong_type_is_zero():
    pred = _pred_obj_all_correct()
    pred["amount_usd"] = "100"  # should be number|null
    res = grade_extraction(json.dumps(pred), _gold())
    assert res["valid_json"] is True
    assert res["schema_valid"] is False
    assert res["total_score"] == 0.0
    assert res["errors"] == ["type_error:amount_usd"]


def test_perfect_prediction_scores_one():
    pred = _pred_obj_all_correct()
    res = grade_extraction(json.dumps(pred), _gold())
    assert res["valid_json"] is True
    assert res["schema_valid"] is True
    assert res["total_score"] == 1.0
    assert res["errors"] == []


def test_string_match_is_case_insensitive():
    pred = _pred_obj_all_correct()
    pred["primary_entity"] = "ftc"  # differs only by case
    res = grade_extraction(json.dumps(pred), _gold())
    assert res["schema_valid"] is True
    assert res["field_correct"]["primary_entity"] is True
    assert res["total_score"] == 1.0


def test_number_tolerance_within_eps_matches():
    g = _gold()
    g2 = dict(g)
    g2["amount_usd"] = 100.0

    pred = _pred_obj_all_correct()
    pred["amount_usd"] = 100.0 + (EPS / 2.0)

    res = grade_extraction(json.dumps(pred), g2)
    assert res["schema_valid"] is True
    assert res["field_correct"]["amount_usd"] is True
    assert res["total_score"] == 1.0


def test_number_tolerance_outside_eps_mismatches():
    g = _gold()
    g2 = dict(g)
    g2["amount_usd"] = 100.0

    pred = _pred_obj_all_correct()
    pred["amount_usd"] = 100.0 + (EPS * 2.0)

    res = grade_extraction(json.dumps(pred), g2)
    assert res["schema_valid"] is True
    assert res["field_correct"]["amount_usd"] is False

    expected = BASE_SCORE + (0.70 - FIELD_WEIGHTS["amount_usd"])
    assert abs(res["total_score"] - expected) < 1e-12
    assert "field_mismatch:amount_usd" in res["errors"]