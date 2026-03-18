"""Shared constants for the extraction_v1 schema."""

SCHEMA_KEYS = {
    "primary_entity",
    "primary_entity_type",
    "secondary_entity",
    "action_type",
    "amount_usd",
    "date",
    "jurisdiction",
}

VALID_ENTITY_TYPES = {"company", "agency", "individual"}
VALID_ACTION_TYPES = {"acquisition", "fine", "lawsuit", "partnership", "investigation"}
VALID_JURISDICTIONS = {"US", "EU", "UK", "Other"}

FIELD_WEIGHTS = {
    "primary_entity": 0.15,
    "primary_entity_type": 0.05,
    "secondary_entity": 0.10,
    "action_type": 0.10,
    "amount_usd": 0.10,
    "date": 0.10,
    "jurisdiction": 0.10,
}

BASE_SCORE = 0.30
EPS = 1e-6

KNOWN_REGULATORS = {
    "FTC",
    "SEC",
    "European Commission",
    "UK Financial Conduct Authority",
    "UK Competition and Markets Authority",
    "Japan's Fair Trade Commission",
}

TASKS_KEYS = {"id", "task_type", "difficulty", "input", "instruction"}
GOLD_KEYS = {"id"} | SCHEMA_KEYS
