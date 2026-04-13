from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class ContentGenerateRequest(BaseModel):
    product_ids: list[UUID] = Field(..., min_length=1)
    campaign_id: UUID
    content_type: str = Field(
        ..., pattern="^(product_description|seo_article|social_post|video_script)$"
    )
    template_id: UUID | None = None


class ContentResponse(BaseModel):
    id: UUID
    product_id: UUID | None
    campaign_id: UUID
    content_type: str
    title: str | None
    body: str
    seo_keywords: list[str] | None
    template_id: UUID | None
    variant: str | None
    claude_model: str | None
    token_cost_input: int | None
    token_cost_output: int | None
    estimated_cost_usd: Decimal | None
    status: str
    platform_variants: dict | None = None
    published_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}  # noqa
