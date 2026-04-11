"""Pydantic schemas for publisher endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class PublishRequest(BaseModel):
    content_id: UUID
    channels: list[str]
    extra_kwargs: dict | None = None


class ScheduleRequest(BaseModel):
    content_id: UUID
    channels: list[str]
    scheduled_at: datetime


class PublicationResponse(BaseModel):
    id: UUID
    content_id: UUID
    platform: str
    channel: str | None
    external_post_id: str | None
    published_at: datetime | None
    status: str

    model_config = {"from_attributes": True}
