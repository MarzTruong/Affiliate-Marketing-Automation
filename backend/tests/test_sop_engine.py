"""Tests for SOP engine: scoring, A/B testing, and utilities."""

import uuid
from decimal import Decimal

import pytest

from backend.models.campaign import Campaign
from backend.models.sop_template import SOPTemplate
from backend.sop_engine.ab_testing import (
    _z_test_proportion,
    conclude_test_manually,
    create_ab_test,
    pick_variant,
    record_impression,
)
from backend.sop_engine.scorer import score_template

# ── Z-test ─────────────────────────────────────────────────────


def test_z_test_equal_proportions():
    """Equal proportions should give high p-value (not significant)."""
    p = _z_test_proportion(100, 10, 100, 10)
    assert p > 0.05


def test_z_test_different_proportions():
    """Very different proportions should give low p-value (significant)."""
    p = _z_test_proportion(1000, 100, 1000, 200)
    assert p < 0.05


def test_z_test_zero_samples():
    p = _z_test_proportion(0, 0, 0, 0)
    assert p == 1.0


def test_z_test_no_conversions():
    p = _z_test_proportion(100, 0, 100, 0)
    assert p == 1.0


# ── A/B Testing ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_ab_test(db):
    campaign = Campaign(id=uuid.uuid4(), name="Test", platform="shopee")
    tmpl_a = SOPTemplate(id=uuid.uuid4(), name="A", content_type="seo_article", prompt_template="A")
    tmpl_b = SOPTemplate(id=uuid.uuid4(), name="B", content_type="seo_article", prompt_template="B")
    db.add_all([campaign, tmpl_a, tmpl_b])
    await db.flush()

    test = await create_ab_test(db, campaign.id, tmpl_a.id, tmpl_b.id, 50)
    assert test.status == "running"
    assert test.sample_size_target == 50


@pytest.mark.asyncio
async def test_create_ab_test_missing_template(db):
    campaign = Campaign(id=uuid.uuid4(), name="Test", platform="shopee")
    tmpl_a = SOPTemplate(id=uuid.uuid4(), name="A", content_type="seo_article", prompt_template="A")
    db.add_all([campaign, tmpl_a])
    await db.flush()

    with pytest.raises(ValueError, match="not found"):
        await create_ab_test(db, campaign.id, tmpl_a.id, uuid.uuid4(), 50)


@pytest.mark.asyncio
async def test_pick_variant_balanced(db):
    campaign = Campaign(id=uuid.uuid4(), name="Test", platform="shopee")
    tmpl_a = SOPTemplate(id=uuid.uuid4(), name="A", content_type="seo_article", prompt_template="A")
    tmpl_b = SOPTemplate(id=uuid.uuid4(), name="B", content_type="seo_article", prompt_template="B")
    db.add_all([campaign, tmpl_a, tmpl_b])
    await db.flush()

    test = await create_ab_test(db, campaign.id, tmpl_a.id, tmpl_b.id, 100)

    # First pick should be A (both at 0)
    v1 = await pick_variant(db, test.id)
    assert v1 == "A"

    # Record impression for A, next should be B
    await record_impression(db, test.id, "A")
    v2 = await pick_variant(db, test.id)
    assert v2 == "B"


@pytest.mark.asyncio
async def test_conclude_test_manually(db):
    campaign = Campaign(id=uuid.uuid4(), name="Test", platform="shopee")
    tmpl_a = SOPTemplate(
        id=uuid.uuid4(),
        name="A",
        content_type="seo_article",
        prompt_template="A",
        performance_score=Decimal("50.00"),
    )
    tmpl_b = SOPTemplate(
        id=uuid.uuid4(),
        name="B",
        content_type="seo_article",
        prompt_template="B",
        performance_score=Decimal("50.00"),
    )
    db.add_all([campaign, tmpl_a, tmpl_b])
    await db.flush()

    test = await create_ab_test(db, campaign.id, tmpl_a.id, tmpl_b.id, 1000)

    # Add some data
    test.variant_a_impressions = 100
    test.variant_a_conversions = 5
    test.variant_b_impressions = 100
    test.variant_b_conversions = 5
    await db.commit()

    result = await conclude_test_manually(db, test.id)
    assert result.status in ("concluded", "inconclusive")


@pytest.mark.asyncio
async def test_conclude_already_concluded(db):
    campaign = Campaign(id=uuid.uuid4(), name="Test", platform="shopee")
    tmpl_a = SOPTemplate(
        id=uuid.uuid4(),
        name="A",
        content_type="seo_article",
        prompt_template="A",
        performance_score=Decimal("50.00"),
    )
    tmpl_b = SOPTemplate(
        id=uuid.uuid4(),
        name="B",
        content_type="seo_article",
        prompt_template="B",
        performance_score=Decimal("50.00"),
    )
    db.add_all([campaign, tmpl_a, tmpl_b])
    await db.flush()

    test = await create_ab_test(db, campaign.id, tmpl_a.id, tmpl_b.id, 10)
    result = await conclude_test_manually(db, test.id)

    with pytest.raises(ValueError, match="already"):
        await conclude_test_manually(db, test.id)


# ── Scoring ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_score_template_no_data(db):
    """Template with no analytics data should score 0."""
    tmpl = SOPTemplate(
        id=uuid.uuid4(), name="Empty", content_type="seo_article", prompt_template="X"
    )
    db.add(tmpl)
    await db.flush()

    score = await score_template(db, tmpl.id)
    assert score == Decimal("0.00")
