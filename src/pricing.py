"""Per-model token pricing and cost calculation."""

# Update when rates change
MODEL_PRICING = {
    "gpt-4o": {
        "input": 2.50 / 1_000_000,
        "output": 10.00 / 1_000_000,
    },
    "gpt-4o-mini": {
        "input": 0.15 / 1_000_000,
        "output": 0.60 / 1_000_000,
    },
}


def compute_cost(model_name, input_tokens, output_tokens):
    """Return cost in USD. Returns None if model not in pricing table or tokens are None."""
    if input_tokens is None or output_tokens is None:
        return None
    pricing = MODEL_PRICING.get(model_name)
    if pricing is None:
        return None
    return input_tokens * pricing["input"] + output_tokens * pricing["output"]
