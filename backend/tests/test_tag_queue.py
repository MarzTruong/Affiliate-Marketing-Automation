"""Test TagQueueService — state management for tag queue items."""
from __future__ import annotations

import uuid

import pytest

from backend.models.tag_queue_item import TagQueueItem
from backend.tiktok_shop.tag_queue import TagQueueService


async def _make_item(db, url: str = "https://tiktok.com/draft/1") -> TagQueueItem:
    svc = TagQueueService(db)
    return await svc.enqueue(
        video_id=uuid.uuid4(),
        tiktok_draft_url=url,
        product_id="sp_test",
        product_name="Sữa Meiji",
        commission_rate=0.15,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_enqueue_creates_item_without_timestamps(db):
    item = await _make_item(db)
    assert item.id is not None
    assert item.tagged_at is None
    assert item.published_at is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_pending_excludes_published(db):
    svc = TagQueueService(db)
    item1 = await _make_item(db, "url1")
    item2 = await _make_item(db, "url2")

    await svc.mark_published(item2.id)

    pending = await svc.list_pending()
    ids = [i.id for i in pending]
    assert item1.id in ids
    assert item2.id not in ids


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mark_tagged_sets_timestamp(db):
    svc = TagQueueService(db)
    item = await _make_item(db)
    await svc.mark_tagged(item.id)
    refreshed = await svc.get(item.id)
    assert refreshed.tagged_at is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mark_published_sets_timestamp(db):
    svc = TagQueueService(db)
    item = await _make_item(db)
    await svc.mark_published(item.id)
    refreshed = await svc.get(item.id)
    assert refreshed.published_at is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mark_tagged_nonexistent_raises_value_error(db):
    svc = TagQueueService(db)
    with pytest.raises(ValueError, match="not found"):
        await svc.mark_tagged(uuid.uuid4())
