"""Test Phase 0 SQLAlchemy models: HookVariant, ProductScore, TagQueueItem."""
import uuid

import pytest

from backend.models.campaign import Campaign
from backend.models.content import ContentPiece
from backend.models.hook_variant import HookVariant
from backend.models.product_score import ProductScore
from backend.models.tag_queue_item import TagQueueItem


@pytest.mark.unit
def test_hook_variant_tablename():
    assert HookVariant.__tablename__ == "hook_variants"


@pytest.mark.unit
def test_product_score_tablename():
    assert ProductScore.__tablename__ == "product_scores"


@pytest.mark.unit
def test_tag_queue_item_tablename():
    assert TagQueueItem.__tablename__ == "tag_queue_items"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_content_piece(db) -> ContentPiece:
    """Create a minimal Campaign + ContentPiece to satisfy FK constraints."""
    campaign = Campaign(id=uuid.uuid4(), name="Phase0 Campaign", platform="tiktok")
    db.add(campaign)
    await db.flush()

    content = ContentPiece(
        id=uuid.uuid4(),
        campaign_id=campaign.id,
        content_type="tiktok_script",
        body="Nội dung video TikTok thử nghiệm Phase 0",
    )
    db.add(content)
    await db.flush()
    return content


# ---------------------------------------------------------------------------
# HookVariant tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hook_variant_instantiation(db):
    content = await _create_content_piece(db)

    hv = HookVariant(
        id=uuid.uuid4(),
        content_piece_id=content.id,
        hook_text="Chị em nào đang đau đầu vì mất ngủ khi mang thai...",
        pattern_type="pain_point",
        retention_at_3s=None,
        score=0.0,
    )
    db.add(hv)
    await db.flush()
    await db.refresh(hv)

    assert hv.id is not None
    assert hv.pattern_type == "pain_point"
    assert hv.score == 0.0
    assert hv.retention_at_3s is None


# ---------------------------------------------------------------------------
# ProductScore tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_product_score_defaults(db):
    ps = ProductScore(
        product_id="tiktok_shop_12345",
        actual_ctr=0.0,
        actual_conversion=0.0,
        return_rate=0.0,
        total_orders=0,
        status="active",
    )
    db.add(ps)
    await db.flush()
    await db.refresh(ps)

    assert ps.status == "active"
    assert ps.total_orders == 0
    assert ps.product_id == "tiktok_shop_12345"


# ---------------------------------------------------------------------------
# TagQueueItem tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tag_queue_item_initial_state(db):
    content = await _create_content_piece(db)

    tqi = TagQueueItem(
        id=uuid.uuid4(),
        video_id=content.id,
        tiktok_draft_url="https://tiktok.com/draft/abc",
        product_id="sp_01",
        product_name="Sữa bột Meiji",
        commission_rate=0.15,
    )
    db.add(tqi)
    await db.flush()
    await db.refresh(tqi)

    assert tqi.tagged_at is None
    assert tqi.published_at is None
    assert tqi.product_id == "sp_01"
    assert tqi.commission_rate == 0.15
