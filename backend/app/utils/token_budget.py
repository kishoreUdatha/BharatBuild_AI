"""
Token Budget & Cost Control Utility

Provides per-request token budget enforcement to prevent runaway costs.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import threading

from app.core.logging_config import logger


@dataclass
class TokenBudget:
    """
    Per-request token budget tracker.

    Usage:
        budget = TokenBudget(max_input_tokens=50000, max_output_tokens=20000)
        budget.consume_input(1500)
        if budget.can_spend_input(8000):
            # proceed with API call
            ...
        budget.consume_output(4000)
    """
    max_input_tokens: int = 100000  # Default: 100K input tokens per request
    max_output_tokens: int = 50000   # Default: 50K output tokens per request
    max_calls: int = 20             # Max LLM calls per request
    max_cost_usd: float = 1.0       # Max cost per request in USD

    # Tracking
    input_tokens_used: int = 0
    output_tokens_used: int = 0
    calls_made: int = 0

    # Cost rates (Claude Sonnet pricing)
    _input_cost_per_1k: float = 0.003
    _output_cost_per_1k: float = 0.015

    def consume_input(self, tokens: int) -> None:
        """Record input token usage."""
        self.input_tokens_used += tokens

    def consume_output(self, tokens: int) -> None:
        """Record output token usage."""
        self.output_tokens_used += tokens

    def record_call(self, input_tokens: int = 0, output_tokens: int = 0) -> None:
        """Record a complete API call."""
        self.input_tokens_used += input_tokens
        self.output_tokens_used += output_tokens
        self.calls_made += 1

    def can_spend_input(self, tokens: int) -> bool:
        """Check if we can afford to spend these input tokens."""
        return (self.input_tokens_used + tokens) <= self.max_input_tokens

    def can_spend_output(self, tokens: int) -> bool:
        """Check if we can afford these output tokens."""
        return (self.output_tokens_used + tokens) <= self.max_output_tokens

    def can_make_call(self) -> bool:
        """Check if we can make another API call."""
        return self.calls_made < self.max_calls

    @property
    def remaining_input(self) -> int:
        """Remaining input tokens."""
        return max(0, self.max_input_tokens - self.input_tokens_used)

    @property
    def remaining_output(self) -> int:
        """Remaining output tokens."""
        return max(0, self.max_output_tokens - self.output_tokens_used)

    @property
    def estimated_cost_usd(self) -> float:
        """Estimated cost in USD so far."""
        input_cost = (self.input_tokens_used / 1000) * self._input_cost_per_1k
        output_cost = (self.output_tokens_used / 1000) * self._output_cost_per_1k
        return input_cost + output_cost

    @property
    def is_budget_exceeded(self) -> bool:
        """Check if any budget limit has been exceeded."""
        return (
            self.input_tokens_used > self.max_input_tokens
            or self.output_tokens_used > self.max_output_tokens
            or self.calls_made > self.max_calls
            or self.estimated_cost_usd > self.max_cost_usd
        )

    def get_recommended_max_tokens(self, default: int = 4096) -> int:
        """Get recommended max_tokens for next API call based on remaining budget."""
        remaining = self.remaining_output
        if remaining <= 0:
            return 0
        return min(default, remaining)

    def to_dict(self) -> Dict[str, Any]:
        """Export budget state."""
        return {
            "input_tokens_used": self.input_tokens_used,
            "output_tokens_used": self.output_tokens_used,
            "calls_made": self.calls_made,
            "max_input_tokens": self.max_input_tokens,
            "max_output_tokens": self.max_output_tokens,
            "max_calls": self.max_calls,
            "estimated_cost_usd": round(self.estimated_cost_usd, 4),
            "budget_exceeded": self.is_budget_exceeded,
        }


# =============================================================================
# PRESETS for different operation types
# =============================================================================

def budget_for_planning() -> TokenBudget:
    """Budget for planning operations (single call, moderate output)."""
    return TokenBudget(
        max_input_tokens=30000,
        max_output_tokens=16384,
        max_calls=3,
        max_cost_usd=0.30,
    )


def budget_for_code_generation() -> TokenBudget:
    """Budget for code generation (multiple files, large output)."""
    return TokenBudget(
        max_input_tokens=80000,
        max_output_tokens=60000,
        max_calls=25,
        max_cost_usd=1.50,
    )


def budget_for_fixing() -> TokenBudget:
    """Budget for error fixing (focused, single file fixes)."""
    return TokenBudget(
        max_input_tokens=20000,
        max_output_tokens=8000,
        max_calls=5,
        max_cost_usd=0.20,
    )


def budget_for_documentation() -> TokenBudget:
    """Budget for document generation (large output)."""
    return TokenBudget(
        max_input_tokens=60000,
        max_output_tokens=80000,
        max_calls=15,
        max_cost_usd=2.00,
    )


def budget_for_classification() -> TokenBudget:
    """Budget for prompt classification (tiny, single call)."""
    return TokenBudget(
        max_input_tokens=2000,
        max_output_tokens=500,
        max_calls=1,
        max_cost_usd=0.01,
    )


# =============================================================================
# TOKEN ESTIMATION
# =============================================================================

def estimate_tokens(text: str) -> int:
    """
    Estimate token count for a string.
    Uses the ~4 chars per token heuristic for English text.
    More accurate than word-based estimation.

    Args:
        text: Text to estimate tokens for

    Returns:
        Estimated token count
    """
    if not text:
        return 0
    # Claude tokenizer averages ~4 characters per token for English
    # Code tends to be ~3.5 chars per token
    return max(1, len(text) // 4)


def estimate_prompt_cost(
    system_prompt: str,
    user_prompt: str,
    expected_output_tokens: int = 4096,
    model: str = "sonnet"
) -> Dict[str, Any]:
    """
    Estimate the cost of an API call before making it.

    Args:
        system_prompt: System prompt text
        user_prompt: User prompt text
        expected_output_tokens: Expected output size
        model: Model name (sonnet, haiku)

    Returns:
        Cost estimation dict
    """
    input_tokens = estimate_tokens(system_prompt) + estimate_tokens(user_prompt)

    # Model-specific pricing
    rates = {
        "sonnet": {"input": 0.003, "output": 0.015},
        "haiku": {"input": 0.00025, "output": 0.00125},
    }
    rate = rates.get(model, rates["sonnet"])

    input_cost = (input_tokens / 1000) * rate["input"]
    output_cost = (expected_output_tokens / 1000) * rate["output"]

    return {
        "estimated_input_tokens": input_tokens,
        "expected_output_tokens": expected_output_tokens,
        "estimated_cost_usd": round(input_cost + output_cost, 4),
        "model": model,
    }
