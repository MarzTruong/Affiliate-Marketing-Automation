"""Pydantic schemas for SOP engine endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class TemplateCreate(BaseModel):
    name: str
    content_type: str
    prompt_template: str
    variables: dict | None = None


class TemplateResponse(BaseModel):
    id: UUID
    name: str
    content_type: str | None
    prompt_template: str
    variables: dict | None
    performance_score: float
    usage_count: int
    avg_conversion_rate: float | None
    avg_ctr: float | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ABTestCreate(BaseModel):
    campaign_id: UUID
    template_a_id: UUID
    template_b_id: UUID
    sample_size_target: int = 100


class ABTestResponse(BaseModel):
    id: UUID
    campaign_id: UUID
    template_a_id: UUID
    template_b_id: UUID
    status: str
    sample_size_target: int
    variant_a_conversions: int
    variant_a_impressions: int
    variant_b_conversions: int
    variant_b_impressions: int
    winner: str | None
    statistical_significance: float | None
    started_at: datetime
    concluded_at: datetime | None

    model_config = {"from_attributes": True}


class ABTestEvent(BaseModel):
    test_id: UUID
    variant: str  # "A" or "B"


class EvolveRequest(BaseModel):
    template_id: UUID


class ScoreResponse(BaseModel):
    template_id: str
    name: str
    score: float
    usage_count: int
