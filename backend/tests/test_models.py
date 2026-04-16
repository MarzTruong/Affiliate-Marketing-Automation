"""Tests for database models."""

import uuid
from decimal import Decimal

import pytest

from backend.models.campaign import Campaign
from backend.models.content import ContentPiece
from backend.models.notification import Notification
from backend.models.product import Product
from backend.models.publication import Publication
from backend.models.sop_template import ABTest, SOPTemplate


@pytest.mark.asyncio
async def test_create_campaign(db, sample_campaign_data):
    campaign = Campaign(
        id=uuid.uuid4(),
        name=sample_campaign_data["name"],
        platform=sample_campaign_data["platform"],
        budget_daily=Decimal(str(sample_campaign_data["budget_daily"])),
        target_category=sample_campaign_data["target_category"],
    )
    db.add(campaign)
    await db.flush()
    await db.refresh(campaign)

    assert campaign.id is not None
    assert campaign.name == "Shopee Fashion Q2 2026"
    assert campaign.platform == "shopee"
    assert campaign.status == "draft"


@pytest.mark.asyncio
async def test_create_product(db, sample_product_data, sample_campaign_data):
    campaign = Campaign(
        id=uuid.uuid4(),
        name=sample_campaign_data["name"],
        platform=sample_campaign_data["platform"],
    )
    db.add(campaign)
    await db.flush()

    product = Product(
        id=uuid.uuid4(),
        campaign_id=campaign.id,
        platform=sample_product_data["platform"],
        external_product_id="123456",
        name=sample_product_data["name"],
        price=Decimal(str(sample_product_data["price"])),
        category=sample_product_data["category"],
        original_url=sample_product_data["original_url"],
    )
    db.add(product)
    await db.flush()

    assert product.name == "Áo Thun Nam Cotton Premium"
    assert product.price == Decimal("199000")


@pytest.mark.asyncio
async def test_create_content_piece(db, sample_campaign_data):
    campaign = Campaign(
        id=uuid.uuid4(),
        name=sample_campaign_data["name"],
        platform=sample_campaign_data["platform"],
    )
    db.add(campaign)
    await db.flush()

    content = ContentPiece(
        id=uuid.uuid4(),
        campaign_id=campaign.id,
        content_type="seo_article",
        title="Top 10 Áo Thun Nam Đẹp Nhất 2026",
        body="Nội dung bài viết SEO...",
        seo_keywords=["áo thun nam", "thời trang nam"],
        status="draft",
    )
    db.add(content)
    await db.flush()

    assert content.content_type == "seo_article"
    assert content.status == "draft"
    assert content.campaign_id == campaign.id


@pytest.mark.asyncio
async def test_create_sop_template(db):
    template = SOPTemplate(
        id=uuid.uuid4(),
        name="Product Description V1",
        content_type="product_description",
        prompt_template="Viết mô tả sản phẩm cho {{ product_name }}",
        performance_score=Decimal("75.50"),
        usage_count=42,
    )
    db.add(template)
    await db.flush()

    assert template.name == "Product Description V1"
    assert template.performance_score == Decimal("75.50")
    assert template.is_active is True


@pytest.mark.asyncio
async def test_create_ab_test(db):
    campaign = Campaign(id=uuid.uuid4(), name="Test Campaign", platform="shopee")
    tmpl_a = SOPTemplate(id=uuid.uuid4(), name="A", content_type="seo_article", prompt_template="A")
    tmpl_b = SOPTemplate(id=uuid.uuid4(), name="B", content_type="seo_article", prompt_template="B")
    db.add_all([campaign, tmpl_a, tmpl_b])
    await db.flush()

    test = ABTest(
        id=uuid.uuid4(),
        campaign_id=campaign.id,
        template_a_id=tmpl_a.id,
        template_b_id=tmpl_b.id,
        sample_size_target=200,
    )
    db.add(test)
    await db.flush()

    assert test.status == "running"
    assert test.sample_size_target == 200
    assert test.variant_a_conversions == 0


@pytest.mark.asyncio
async def test_create_publication(db):
    campaign = Campaign(id=uuid.uuid4(), name="Pub Campaign", platform="shopee")
    db.add(campaign)
    await db.flush()

    content = ContentPiece(
        id=uuid.uuid4(), campaign_id=campaign.id, content_type="social_post", body="Test"
    )
    db.add(content)
    await db.flush()

    pub = Publication(
        id=uuid.uuid4(),
        content_id=content.id,
        platform="facebook",
        channel="facebook",
        status="pending",
    )
    db.add(pub)
    await db.flush()

    assert pub.status == "pending"
    assert pub.platform == "facebook"


@pytest.mark.asyncio
async def test_create_notification(db):
    notif = Notification(
        id=uuid.uuid4(),
        type="fraud",
        title="Click spam detected",
        message="IP 1.2.3.4 generated 50 clicks in 1 hour",
        severity="warning",
    )
    db.add(notif)
    await db.flush()

    assert notif.is_read is False
    assert notif.severity == "warning"
