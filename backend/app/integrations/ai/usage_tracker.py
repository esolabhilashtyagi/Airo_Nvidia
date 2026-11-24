import logging
from datetime import date
from typing import Dict, Optional
from app.integrations.ai.base import TokenUsage

logger = logging.getLogger("aairo.ai.usage")

# Gemini pricing estimates (per million tokens)
PRICING_ESTIMATES = {
    "gemini-2.5-flash": {
        "prompt": 0.075 / 1_000_000,
        "completion": 0.30 / 1_000_000,
    },
    "gemini-3.8-flash": {
        "prompt": 0.75 / 1_000_000,
        "completion": 3.75 / 1_000_000,
    },
    "gemini-1.5-flash": {
        "prompt": 0.075 / 1_000_000,
        "completion": 0.30 / 1_000_000,
    },
    "gemini-1.5-pro": {
        "prompt": 3.50 / 1_000_000,
        "completion": 10.50 / 1_000_000,
    }
}


class UsageTracker:
    def __init__(self):
        self.total_prompt_tokens: int = 0
        self.total_completion_tokens: int = 0
        self.total_cost_usd: float = 0.0
        self.unpriced_usage_events: int = 0

    def calculate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> Optional[float]:
        rates = PRICING_ESTIMATES.get(model)
        if rates is None:
            logger.warning("No pricing estimate configured for model %s", model)
            return None
        if model == "gemini-3.8-flash" and date.today() >= date(2027, 1, 1):
            # Introductory pricing expires 2026-12-31; then standard pricing applies.
            rates = {"prompt": 1.50 / 1_000_000, "completion": 7.50 / 1_000_000}
        cost = (prompt_tokens * rates["prompt"]) + (completion_tokens * rates["completion"])
        return round(cost, 6)

    def record_usage(self, model: str, prompt_tokens: int, completion_tokens: int) -> TokenUsage:
        cost = self.calculate_cost(model, prompt_tokens, completion_tokens)
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens
        if cost is None:
            self.unpriced_usage_events += 1
        else:
            self.total_cost_usd += cost

        usage = TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            estimated_cost_usd=cost
        )
        if cost is None:
            logger.info("AI Usage [%s]: %s tokens (cost estimate unavailable)", model, usage.total_tokens)
        else:
            logger.info("AI Usage [%s]: %s tokens (~$%.6f)", model, usage.total_tokens, cost)
        return usage


usage_tracker = UsageTracker()
