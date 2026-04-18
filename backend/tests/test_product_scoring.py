"""Test ProductScoringEngine — Loop 5."""
from __future__ import annotations

import pytest

from backend.learning.product_scoring import (
    RETURN_RATE_BLACKLIST_THRESHOLD,
    ProductScoringEngine,
)
from backend.models.product_score import ProductScore


@pytest.mark.unit
@pytest.mark.asyncio
async def test_record_creates_new_product(db):
    eng = ProductScoringEngine(db)
    await eng.record_performance(
        product_id="sp_new",
        ctr=0.012,
        conversion=0.025,
        return_rate=0.10,
        orders_delta=5,
    )
    row = await db.get(ProductScore, "sp_new")
    assert row is not None
    assert row.actual_ctr == pytest.approx(0.012)
    assert row.total_orders == 5
    assert row.status == "active"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_high_return_rate_blacklists(db):
    eng = ProductScoringEngine(db)
    await eng.record_performance(
        product_id="sp_bad",
        ctr=0.01,
        conversion=0.02,
        return_rate=0.30,  # >= 0.25 threshold
        orders_delta=10,
    )
    row = await db.get(ProductScore, "sp_bad")
    assert row.status == "blacklisted"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ema_updates_on_subsequent_calls(db):
    eng = ProductScoringEngine(db)
    await eng.record_performance(
        product_id="sp_ema",
        ctr=0.01,
        conversion=0.02,
        return_rate=0.05,
        orders_delta=1,
    )
    await eng.record_performance(
        product_id="sp_ema",
        ctr=0.02,
        conversion=0.03,
        return_rate=0.06,
        orders_delta=2,
    )
    row = await db.get(ProductScore, "sp_ema")
    # EMA: 0.3*0.02 + 0.7*0.01 = 0.013
    assert row.actual_ctr == pytest.approx(0.013)
    assert row.total_orders == 3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_active_excludes_blacklisted(db):
    eng = ProductScoringEngine(db)
    await eng.record_performance(
        product_id="sp_ok",
        ctr=0.01, conversion=0.02, return_rate=0.05, orders_delta=1,
    )
    await eng.record_performance(
        product_id="sp_bad",
        ctr=0.01, conversion=0.02, return_rate=0.40, orders_delta=1,
    )
    active = await eng.list_active()
    ids = [p.product_id for p in active]
    assert "sp_ok" in ids
    assert "sp_bad" not in ids


@pytest.mark.unit
def test_blacklist_threshold_is_correct():
    assert RETURN_RATE_BLACKLIST_THRESHOLD == 0.25
