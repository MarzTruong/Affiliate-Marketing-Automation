"""FastAPI router for Tag Queue endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.tiktok_shop.tag_queue import TagQueueService

router = APIRouter(prefix="/api/tag-queue", tags=["tag-queue"])


class TagQueueItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    video_id: uuid.UUID
    tiktok_draft_url: str
    product_id: str
    product_name: str
    commission_rate: float
    tagged_at: datetime | None
    published_at: datetime | None


@router.get("/pending", response_model=list[TagQueueItemOut])
async def list_pending(db: AsyncSession = Depends(get_db)) -> list[TagQueueItemOut]:
    svc = TagQueueService(db)
    return [TagQueueItemOut.model_validate(i) for i in await svc.list_pending()]


@router.post("/{item_id}/tagged")
async def mark_tagged(
    item_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    svc = TagQueueService(db)
    try:
        await svc.mark_tagged(item_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return {"status": "ok"}


@router.post("/{item_id}/published")
async def mark_published(
    item_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    svc = TagQueueService(db)
    try:
        await svc.mark_published(item_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return {"status": "ok"}
