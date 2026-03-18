from src.pricing import compute_cost


def test_gpt4o_mini_cost():
    # 1000 input tokens, 500 output tokens
    cost = compute_cost("gpt-4o-mini", 1000, 500)
    expected = 1000 * (0.15 / 1_000_000) + 500 * (0.60 / 1_000_000)
    assert abs(cost - expected) < 1e-12


def test_gpt4o_cost():
    cost = compute_cost("gpt-4o", 1000, 500)
    expected = 1000 * (2.50 / 1_000_000) + 500 * (10.00 / 1_000_000)
    assert abs(cost - expected) < 1e-12


def test_unknown_model_returns_none():
    assert compute_cost("unknown-model", 1000, 500) is None


def test_none_tokens_returns_none():
    assert compute_cost("gpt-4o", None, 500) is None
    assert compute_cost("gpt-4o", 1000, None) is None
