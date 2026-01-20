"""
AI Cost Calculator

Calculates API costs based on token usage and model pricing.
"""

from enum import Enum


class AIModel(str, Enum):
    """Available AI models"""

    CLAUDE_HAIKU = "claude-3-5-haiku-20241022"
    CLAUDE_SONNET = "claude-sonnet-4-20250514"
    CLAUDE_OPUS = "claude-opus-4-20250514"


# Pricing as of January 2025 (USD per token)
MODEL_PRICING = {
    AIModel.CLAUDE_OPUS: {
        "input": 15.00 / 1_000_000,  # $15 per MTok
        "output": 75.00 / 1_000_000,  # $75 per MTok
    },
    AIModel.CLAUDE_SONNET: {
        "input": 3.00 / 1_000_000,  # $3 per MTok
        "output": 15.00 / 1_000_000,  # $15 per MTok
    },
    AIModel.CLAUDE_HAIKU: {
        "input": 0.25 / 1_000_000,  # $0.25 per MTok
        "output": 1.25 / 1_000_000,  # $1.25 per MTok
    },
}


def calculate_cost(model: AIModel, input_tokens: int, output_tokens: int) -> float:
    """
    Calculate API cost in USD

    Args:
        model: AI model used
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens

    Returns:
        Estimated cost in USD
    """
    rates = MODEL_PRICING.get(model, MODEL_PRICING[AIModel.CLAUDE_HAIKU])
    return (input_tokens * rates["input"]) + (output_tokens * rates["output"])
