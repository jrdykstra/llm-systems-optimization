"""Shared constants for the antitrust_v1 schema."""

SCHEMA_KEYS = {
    "case_name",
    "plaintiff",
    "defendant",
    "court",
    "date_filed",
    "cause_of_action",
    "statute",
    "market_definition",
    "remedy_sought",
    "holding",
}

VALID_CAUSES = {
    "bid_rigging",
    "price_fixing",
    "monopolization",
    "merger_challenge",
    "wage_fixing",
    "algorithmic_pricing",
}

VALID_REMEDIES = {
    "criminal_penalty",
    "injunctive_relief",
    "divestiture",
    "consent_decree",
    "damages",
}

VALID_HOLDINGS = {
    "guilty_plea",
    "convicted",
    "settled",
    "dismissed",
    "pending",
    "approved",
}

FIELD_WEIGHTS = {
    "case_name": 0.05,
    "plaintiff": 0.10,
    "defendant": 0.10,
    "court": 0.05,
    "date_filed": 0.05,
    "cause_of_action": 0.15,
    "statute": 0.05,
    "market_definition": 0.10,
    "remedy_sought": 0.10,
    "holding": 0.05,
}

BASE_SCORE = 0.20

TASKS_KEYS = {"id", "task_type", "difficulty", "input", "instruction"}
GOLD_KEYS = {"id"} | SCHEMA_KEYS
