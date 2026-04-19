"""FastAPI router for TikTok Shop — Tag Queue + Product Search."""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.tiktok_shop.connector import TikTokShopAuthError, get_connector
from backend.tiktok_shop.product_search import ProductResult, ProductSearchClient
from backend.tiktok_shop.tag_queue import TagQueueService

router = APIRouter(prefix="/api/tag-queue", tags=["tag-queue"])
products_router = APIRouter(prefix="/api/v1/tiktok-shop", tags=["tiktok-shop"])


class ProductOut(BaseModel):
    product_id: str
    product_name: str
    price: float
    commission_rate: float
    category_name: str


@products_router.get("/products/search", response_model=list[ProductOut])
async def search_products(
    keyword: str,
    limit: int = 20,
    min_commission: float = 0.10,
) -> list[ProductOut]:
    """Search TikTok Shop Affiliate Creator products theo keyword."""
    try:
        connector = get_connector()
    except TikTokShopAuthError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e

    client = ProductSearchClient(connector)
    try:
        results: list[ProductResult] = await client.search(
            keyword=keyword,
            limit=limit,
            min_commission_rate=min_commission,
        )
    except TikTokShopAuthError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"TikTok Shop API lỗi: {e}") from e

    return [ProductOut(**r.__dict__) for r in results]


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
