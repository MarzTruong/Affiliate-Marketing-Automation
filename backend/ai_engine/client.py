import anthropic
from jinja2 import Template

from backend.ai_engine.cost_tracker import CostTracker
from backend.ai_engine.prompts.system import build_system_message
from backend.config import settings


class DailyCostLimitError(RuntimeError):
    """Raised when the daily Claude API cost limit is exceeded."""


class ClaudeClient:
    """Wrapper around Anthropic SDK with cost tracking and model routing."""

    MODEL_ROUTING = {
        "product_description": "claude-haiku-4-5-20251001",
        "seo_article": "claude-sonnet-4-6",
        "social_post": "claude-haiku-4-5-20251001",
        "video_script": "claude-sonnet-4-6",
    }

    MAX_TOKENS = {
        "product_description": 1000,
        "seo_article": 4000,
        "social_post": 500,
        "video_script": 2000,
    }

    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.cost_tracker = CostTracker()

    async def generate(
        self,
        content_type: str,
        variables: dict,
        template: str,
        model_override: str | None = None,
        max_tokens: int | None = None,
    ) -> tuple[str, dict]:
        """Generate content using Claude API.

        Returns (content_text, usage_metadata).
        """
        model = model_override or self.MODEL_ROUTING.get(content_type, "claude-haiku-4-5-20251001")
        max_tok = max_tokens or self.MAX_TOKENS.get(content_type, 2000)

        # Check daily cost limit
        daily_total = self.cost_tracker.get_daily_total()
        if daily_total >= settings.claude_daily_cost_limit_usd:
            raise DailyCostLimitError(
                f"Daily Claude API cost limit reached: ${daily_total:.2f} / ${settings.claude_daily_cost_limit_usd}"
            )

        # Render prompt template
        prompt = Template(template).render(**variables)

        # BASE_SYSTEM được cache ephemeral (giảm chi phí token lặp lại)
        # TASK_CONTEXT thay đổi theo content_type — không cache
        system_message = build_system_message(content_type)
        response = await self.client.messages.create(
            model=model,
            max_tokens=max_tok,
            system=[
                {
                    "type": "text",
                    "text": system_message,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": prompt}],
        )

        if not response.content:
            raise ValueError(f"Claude API returned empty content for model {model}")
        content = response.content[0].text
        usage = self.cost_tracker.record(
            model,
            {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
        )

        return content, usage
