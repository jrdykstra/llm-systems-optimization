import json
from src.run_cascade import should_escalate, should_escalate_antitrust


def test_valid_schema_no_escalate():
    obj = {
        "primary_entity": "Nvidia",
        "primary_entity_type": "company",
        "secondary_entity": "Run:ai",
        "action_type": "acquisition",
        "amount_usd": 700000000,
        "date": "2024-04-24",
        "jurisdiction": None
    }
    escalate, reasons = should_escalate(json.dumps(obj))
    assert escalate is False


def test_invalid_json_escalates():
    escalate, reasons = should_escalate("not json at all")
    assert escalate is True
    assert "no_json_object" in reasons


def test_schema_error_escalates():
    obj = {"primary_entity": "Nvidia"}  # missing fields
    escalate, reasons = should_escalate(json.dumps(obj))
    assert escalate is True
    assert any("missing_keys" in r for r in reasons)


def test_lawsuit_company_primary_escalates():
    obj = {
        "primary_entity": "Amazon",
        "primary_entity_type": "company",
        "secondary_entity": "FTC",
        "action_type": "lawsuit",
        "amount_usd": None,
        "date": "2023-06-21",
        "jurisdiction": "US",
    }
    escalate, reasons = should_escalate(json.dumps(obj))
    assert escalate is True
    assert "heuristic:lawsuit_role_swap" in reasons


def test_lawsuit_agency_primary_no_escalate():
    obj = {
        "primary_entity": "FTC",
        "primary_entity_type": "agency",
        "secondary_entity": "Amazon",
        "action_type": "lawsuit",
        "amount_usd": None,
        "date": "2023-06-21",
        "jurisdiction": "US",
    }
    escalate, reasons = should_escalate(json.dumps(obj))
    assert escalate is False


def test_jurisdiction_other_unknown_regulator_escalates():
    obj = {
        "primary_entity": "Google",
        "primary_entity_type": "company",
        "secondary_entity": "India's Competition Commission",
        "action_type": "fine",
        "amount_usd": 162000000,
        "date": "2022-10-20",
        "jurisdiction": "Other",
    }
    escalate, reasons = should_escalate(json.dumps(obj))
    assert escalate is True
    assert "heuristic:jurisdiction_other_unknown_regulator" in reasons


def test_jurisdiction_other_known_regulator_no_escalate():
    obj = {
        "primary_entity": "Google",
        "primary_entity_type": "company",
        "secondary_entity": "Japan's Fair Trade Commission",
        "action_type": "investigation",
        "amount_usd": None,
        "date": "2024-01-01",
        "jurisdiction": "Other",
    }
    escalate, reasons = should_escalate(json.dumps(obj))
    assert escalate is False


def test_antitrust_valid_no_escalate():
    obj = {
        "case_name": "United States v. LivCor",
        "plaintiff": "DOJ Antitrust Division",
        "defendant": "LivCor",
        "court": None,
        "date_filed": None,
        "cause_of_action": "algorithmic_pricing",
        "statute": None,
        "market_definition": "residential rental market",
        "remedy_sought": "consent_decree",
        "holding": "settled",
    }
    escalate, reasons = should_escalate_antitrust(json.dumps(obj))
    assert escalate is False


def test_antitrust_plaintiff_not_government_escalates():
    obj = {
        "case_name": "United States v. LivCor",
        "plaintiff": "LivCor",
        "defendant": "DOJ Antitrust Division",
        "court": None,
        "date_filed": None,
        "cause_of_action": "algorithmic_pricing",
        "statute": None,
        "market_definition": "residential rental market",
        "remedy_sought": "consent_decree",
        "holding": "settled",
    }
    escalate, reasons = should_escalate_antitrust(json.dumps(obj))
    assert escalate is True
    assert "heuristic:plaintiff_not_government" in reasons


