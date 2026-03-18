# src/grading.py
"""
Deterministic grader for extraction_v1 (router_v1).

Contract (Week 1):
- If prediction is not valid JSON OR does not conform to schema: score = 0.00
- If schema-valid: score = 0.30 base + sum(field weights for correct fields) (weights sum to 0.70)
- No partial credit if schema invalid.

Schema (exact keys, no extras):
- primary_entity: str
- primary_entity_type: enum {"company","agency","individual"}
- secondary_entity: str | null
- action_type: enum {"acquisition","fine","lawsuit","partnership","investigation"}
- amount_usd: number | null
- date: "YYYY-MM-DD" | null
- jurisdiction: enum {"US","EU","UK","Other"} | null

Field comparison rules:
- string: case-insensitive exact match (strip + lower)
- enum: exact match
- number: both null match OR abs(pred-gold) <= 1e-6
- date: exact string match (gold expected already normalized)
- null: both must be null
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from src.schema.extraction import (
    SCHEMA_KEYS, VALID_ENTITY_TYPES, VALID_ACTION_TYPES,
    VALID_JURISDICTIONS, FIELD_WEIGHTS, BASE_SCORE, EPS,
)

JsonDict = Dict[str, Any]

# ---------- Parsing: raw model text -> dict ----------
def extract_first_json_object(text: str) -> Tuple[Optional[str], List[str]]:
    """
    Deterministically extract the first top-level JSON object substring from text.

    Useful when model output wraps JSON in prose or markdown.
    This function does NOT validate JSON; it only returns a candidate substring.

    Error codes:
      - empty_pred
      - no_json_object
      - unbalanced_braces
    """
    s = text.strip()
    if not s:
        return None, ["empty_pred"]

    start = s.find("{")
    if start == -1:
        return None, ["no_json_object"]

    depth = 0
    in_str = False
    escape = False

    for i in range(start, len(s)):
        ch = s[i]

        if in_str:
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if ch == '"':
                in_str = False
            continue

        if ch == '"':
            in_str = True
            continue

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return s[start : i + 1], []

    return None, ["unbalanced_braces"]


def parse_pred_object(
    pred_text: str,
    *,
    allow_embedded_json: bool = True,
) -> Tuple[Optional[JsonDict], List[str]]:
    """
    Parse model output into a single JSON object dict.

    Error codes:
      - empty_pred
      - no_json_object
      - unbalanced_braces
      - invalid_json
      - pred_not_object
    """
    s = pred_text.strip()
    if not s:
        return None, ["empty_pred"]

    raw = s

    if allow_embedded_json:
        extracted, errs = extract_first_json_object(s)
        if extracted is not None:
            raw = extracted
        elif s[0] in ("{", "["):
            raw = s
        else:
            return None, errs

    try:
        obj = json.loads(raw)
    except Exception:
        return None, ["invalid_json"]

    if not isinstance(obj, dict):
        return None, ["pred_not_object"]

    return obj, []


# ---------- Schema validation: prediction only ----------
def validate_keys_exact(pred_obj: JsonDict) -> List[str]:
    actual = set(pred_obj.keys())
    missing = SCHEMA_KEYS - actual
    extra = actual - SCHEMA_KEYS
    errors: List[str] = []
    if missing:
        errors.append("missing_keys:" + ",".join(sorted(missing)))
    if extra:
        errors.append("extra_keys:" + ",".join(sorted(extra)))
    return errors


def _is_number(x: Any) -> bool:
    # bool is a subclass of int; exclude it.
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def validate_types(pred_obj: JsonDict) -> List[str]:
    errors: List[str] = []

    if not isinstance(pred_obj["primary_entity"], str):
        errors.append("type_error:primary_entity")

    if not isinstance(pred_obj["primary_entity_type"], str):
        errors.append("type_error:primary_entity_type")

    se = pred_obj["secondary_entity"]
    if se is not None and not isinstance(se, str):
        errors.append("type_error:secondary_entity")

    if not isinstance(pred_obj["action_type"], str):
        errors.append("type_error:action_type")

    amt = pred_obj["amount_usd"]
    if amt is not None and not _is_number(amt):
        errors.append("type_error:amount_usd")

    dt = pred_obj["date"]
    if dt is not None and not isinstance(dt, str):
        errors.append("type_error:date")

    jur = pred_obj["jurisdiction"]
    if jur is not None and not isinstance(jur, str):
        errors.append("type_error:jurisdiction")

    return errors


def validate_enums(pred_obj: JsonDict) -> List[str]:
    errors: List[str] = []

    if pred_obj["primary_entity_type"] not in VALID_ENTITY_TYPES:
        errors.append("enum_error:primary_entity_type")

    if pred_obj["action_type"] not in VALID_ACTION_TYPES:
        errors.append("enum_error:action_type")

    jur = pred_obj["jurisdiction"]
    if jur is not None and jur not in VALID_JURISDICTIONS:
        errors.append("enum_error:jurisdiction")

    return errors


def validate_schema(pred_obj: JsonDict) -> List[str]:
    """
    Deterministic fail-fast schema validation.
    Returns [] if valid; else returns a list of error codes.

    Order: keys -> types -> enums
    """
    key_errs = validate_keys_exact(pred_obj)
    if key_errs:
        return key_errs

    type_errs = validate_types(pred_obj)
    if type_errs:
        return type_errs

    enum_errs = validate_enums(pred_obj)
    if enum_errs:
        return enum_errs

    return []


# ---------- Field comparison: uses gold ----------
def match_string_ci(a: Any, b: Any) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return isinstance(a, str) and isinstance(b, str) and a.strip().lower() == b.strip().lower()


def match_enum(a: Any, b: Any) -> bool:
    return a == b


def match_number(a: Any, b: Any) -> bool:
    if a is None or b is None:
        return a is None and b is None
    if not _is_number(a) or not _is_number(b):
        return False
    return abs(float(a) - float(b)) <= EPS


def match_date(a: Any, b: Any) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return isinstance(a, str) and isinstance(b, str) and a == b


def compute_field_correct(pred_obj: JsonDict, gold_obj: JsonDict) -> Dict[str, bool]:
    """
    Compare each field to gold using extraction_v1 comparison rules.
    Assumes pred_obj is schema-valid.
    """
    return {
        "primary_entity": match_string_ci(pred_obj["primary_entity"], gold_obj["primary_entity"]),
        "primary_entity_type": match_enum(pred_obj["primary_entity_type"], gold_obj["primary_entity_type"]),
        "secondary_entity": match_string_ci(pred_obj["secondary_entity"], gold_obj["secondary_entity"]),
        "action_type": match_enum(pred_obj["action_type"], gold_obj["action_type"]),
        "amount_usd": match_number(pred_obj["amount_usd"], gold_obj["amount_usd"]),
        "date": match_date(pred_obj["date"], gold_obj["date"]),
        "jurisdiction": match_enum(pred_obj["jurisdiction"], gold_obj["jurisdiction"]),
    }


def compute_total_score(field_correct: Dict[str, bool]) -> float:
    add = 0.0
    for field, ok in field_correct.items():
        if ok:
            add += FIELD_WEIGHTS[field]
    total = BASE_SCORE + add
    return max(0.0, min(1.0, total))


# ---------- Public API ----------
def grade_extraction(pred_text: str, gold_obj: JsonDict) -> JsonDict:
    """
    Grade raw model output text against a gold label dict.

    Returns a structured result dict with deterministic fields:
      - gold_id
      - valid_json
      - schema_valid
      - base_score
      - field_correct
      - field_scores
      - total_score
      - errors
    """
    gold_id = gold_obj.get("id")

    result: JsonDict = {
        "gold_id": gold_id,
        "valid_json": False,
        "schema_valid": False,
        "base_score": 0.0,
        "field_correct": {},
        "field_scores": {},
        "total_score": 0.0,
        "errors": [],
    }

    pred_obj, parse_errors = parse_pred_object(pred_text, allow_embedded_json=True)
    if pred_obj is None:
        result["errors"] = parse_errors
        return result

    result["valid_json"] = True

    schema_errors = validate_schema(pred_obj)
    if schema_errors:
        result["errors"] = schema_errors
        return result

    result["schema_valid"] = True
    result["base_score"] = BASE_SCORE

    field_correct = compute_field_correct(pred_obj, gold_obj)
    field_scores = {f: (FIELD_WEIGHTS[f] if ok else 0.0) for f, ok in field_correct.items()}
    errors = [f"field_mismatch:{f}" for f, ok in field_correct.items() if not ok]

    result["field_correct"] = field_correct
    result["field_scores"] = field_scores
    result["total_score"] = compute_total_score(field_correct)
    result["errors"] = errors
    return result