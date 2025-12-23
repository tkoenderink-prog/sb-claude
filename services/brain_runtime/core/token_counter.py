"""Token counting and cost calculation utilities for Phase 9."""


# Pricing per million tokens (as of 2025-01)
MODEL_PRICING = {
    "claude-opus-4-5-20251101": {
        "input": 5.0,
        "output": 25.0,
        "cache_write": 6.25,  # 1.25x input price
        "cache_read": 0.5,  # 10% of input price
    },
    "claude-sonnet-4-5-20250929": {
        "input": 3.0,
        "output": 15.0,
        "cache_write": 3.75,
        "cache_read": 0.3,
    },
    "claude-haiku-4-5-20251001": {
        "input": 1.0,
        "output": 5.0,
        "cache_write": 1.25,
        "cache_read": 0.1,
    },
    "claude-3-5-haiku-20241022": {
        "input": 0.8,
        "output": 4.0,
        "cache_write": 1.0,
        "cache_read": 0.08,
    },
    # Sonnet 4 (non-4.5) - older model
    "claude-sonnet-4-20250514": {
        "input": 3.0,
        "output": 15.0,
        "cache_write": 3.75,
        "cache_read": 0.3,
    },
}

# Context window sizes per model
MODEL_CONTEXT_WINDOWS = {
    "claude-opus-4-5-20251101": 200_000,
    "claude-sonnet-4-5-20250929": 200_000,
    "claude-haiku-4-5-20251001": 200_000,
    "claude-3-5-haiku-20241022": 200_000,
    "claude-sonnet-4-20250514": 200_000,
}

# Default pricing for unknown models
DEFAULT_PRICING = {
    "input": 3.0,
    "output": 15.0,
    "cache_write": 3.75,
    "cache_read": 0.3,
}


def get_model_pricing(model: str) -> dict:
    """Get pricing for a model, falling back to defaults for unknown models."""
    return MODEL_PRICING.get(model, DEFAULT_PRICING)


def get_context_window(model: str) -> int:
    """Get context window size for a model."""
    return MODEL_CONTEXT_WINDOWS.get(model, 200_000)


def calculate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_creation_tokens: int = 0,
    cache_read_tokens: int = 0,
) -> float:
    """Calculate cost in USD for a message exchange.

    Returns cost in dollars (e.g., 0.0351).
    """
    pricing = get_model_pricing(model)

    # Input tokens = regular input + cache writes (at higher rate)
    # Cache reads are charged at reduced rate
    regular_input = max(0, input_tokens - cache_creation_tokens)
    input_cost = regular_input * pricing["input"]
    cache_write_cost = cache_creation_tokens * pricing["cache_write"]
    cache_read_cost = cache_read_tokens * pricing["cache_read"]
    output_cost = output_tokens * pricing["output"]

    total = (input_cost + cache_write_cost + cache_read_cost + output_cost) / 1_000_000
    return round(total, 6)


def calculate_cost_microdollars(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_creation_tokens: int = 0,
    cache_read_tokens: int = 0,
) -> int:
    """Calculate cost in microdollars (millionths of a dollar) for database storage.

    This avoids floating point precision issues.
    """
    cost_usd = calculate_cost(
        model, input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens
    )
    return int(cost_usd * 1_000_000)


def format_tokens(count: int) -> str:
    """Format token count for display (e.g., '2.4K', '1.2M')."""
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    elif count >= 1_000:
        return f"{count / 1_000:.1f}K"
    return str(count)


def format_cost(cost_usd: float) -> str:
    """Format cost for display (e.g., '$0.08', '$1.25')."""
    if cost_usd < 0.01:
        return f"${cost_usd:.4f}"
    elif cost_usd < 1:
        return f"${cost_usd:.2f}"
    else:
        return f"${cost_usd:.2f}"
