from datetime import date
from decimal import Decimal

# Pricing per million tokens (as of 2026)
MODEL_PRICING = {
    "claude-haiku-4-5-20251001": {"input": Decimal("1.00"), "output": Decimal("5.00")},
    "claude-sonnet-4-6": {"input": Decimal("3.00"), "output": Decimal("15.00")},
    "claude-opus-4-6": {"input": Decimal("15.00"), "output": Decimal("75.00")},
}


class CostTracker:
    """Track Claude API usage and costs."""

    def __init__(self):
        self._daily_totals: dict[str, Decimal] = {}

    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> Decimal:
        pricing = MODEL_PRICING.get(model)
        if not pricing:
            # Fallback to Haiku pricing
            pricing = MODEL_PRICING["claude-haiku-4-5-20251001"]

        input_cost = (Decimal(input_tokens) / Decimal("1000000")) * pricing["input"]
        output_cost = (Decimal(output_tokens) / Decimal("1000000")) * pricing["output"]
        return input_cost + output_cost

    def record(self, model: str, usage: dict) -> dict:
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        cost = self.calculate_cost(model, input_tokens, output_tokens)

        today = date.today().isoformat()
        self._daily_totals[today] = self._daily_totals.get(today, Decimal("0")) + cost

        return {
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": float(cost),
            "daily_total_usd": float(self._daily_totals[today]),
        }

    def get_daily_total(self, day: date | None = None) -> Decimal:
        key = (day or date.today()).isoformat()
        return self._daily_totals.get(key, Decimal("0"))
