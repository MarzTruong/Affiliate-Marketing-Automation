"""TagQueueService — state manager for videos awaiting manual TikTok SP tagging."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.tag_queue_item import TagQueueItem


class TagQueueService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def enqueue(
        self,
        *,
        video_id: uuid.UUID,
        tiktok_draft_url: str,
        product_id: str,
        product_name: str,
        commission_rate: float,
    ) -> TagQueueItem:
        item = TagQueueItem(
            id=uuid.uuid4(),
            video_id=video_id,
            tiktok_draft_url=tiktok_draft_url,
            product_id=product_id,
            product_name=product_name,
            commission_rate=commission_rate,
        )
        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def list_pending(self) -> list[TagQueueItem]:
        """Return items not yet published, ordered by creation time."""
        stmt = (
            select(TagQueueItem)
            .where(TagQueueItem.published_at.is_(None))
            .order_by(TagQueueItem.created_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get(self, item_id: uuid.UUID) -> TagQueueItem | None:
        return await self.db.get(TagQueueItem, item_id)

    async def mark_tagged(self, item_id: uuid.UUID) -> None:
        """Set tagged_at timestamp. Raises ValueError if not found."""
        item = await self.get(item_id)
        if item is None:
            raise ValueError(f"TagQueueItem {item_id} not found")
        item.tagged_at = datetime.now(timezone.utc)
        await self.db.commit()

    async def mark_published(self, item_id: uuid.UUID) -> None:
        """Set published_at timestamp. Raises ValueError if not found."""
        item = await self.get(item_id)
        if item is None:
            raise ValueError(f"TagQueueItem {item_id} not found")
        item.published_at = datetime.now(timezone.utc)
        await self.db.commit()
