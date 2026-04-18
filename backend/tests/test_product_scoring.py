"""Test ProductScoringEngine — Loop 5 product performance learner."""

from __future__ import annotations

import math

import pytest

from backend.learning.product_scoring import ProductScoringEngine


@pytest.mark.unit
@pytest.mark.asyncio
async def test_record_performance_creates_row(db):
    eng = ProductScoringEngine(db)
    ps = await eng.record_performance(
        product_id="sp_meiji",
        ctr=0.05,
        conversion=0.03,
        return_rate=0.05,
        orders_delta=10,
    )
    assert ps.id is not None
    assert ps.product_id == "sp_meiji"
    assert ps.ctr == pytest.approx(0.05)
    assert ps.conversion == pytest.approx(0.03)
    assert ps.return_rate == pytest.approx(0.05)
    assert ps.orders_delta == 10


@pytest.mark.unit
@pytest.mark.asyncio
async def test_score_formula_is_correct(db):
    """Score = ctr*40 + conversion*50 - return_rate*30 + log1p(orders_delta)*10"""
    eng = ProductScoringEngine(db)
    ctr, conv, rr, od = 0.1, 0.05, 0.02, 5
    expected = ctr * 40 + conv * 50 - rr * 30 + math.log1p(od) * 10
    ps = await eng.record_performance(
        product_id="sp_score",
        ctr=ctr,
        conversion=conv,
        return_rate=rr,
        orders_delta=od,
    )
    assert ps.score == pytest.approx(expected, rel=1e-5)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_empty_product_id_raises_value_error(db):
    eng = ProductScoringEngine(db)
    with pytest.raises(ValueError, match="product_id must not be empty"):
        await eng.record_performance(
            product_id="   ",
            ctr=0.01,
            conversion=0.01,
            return_rate=0.01,
            orders_delta=0,
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_top_products_returns_descending_score(db):
    eng = ProductScoringEngine(db)
    # low score
    await eng.record_performance(
        product_id="low",
        ctr=0.001,
        conversion=0.001,
        return_rate=0.5,
        orders_delta=0,
    )
    # high score
    await eng.record_performance(
        product_id="high",
        ctr=0.2,
        conversion=0.1,
        return_rate=0.01,
        orders_delta=100,
    )
    top = await eng.top_products(limit=2)
    assert len(top) == 2
    assert top[0].score >= top[1].score
    assert top[0].product_id == "high"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_negative_orders_delta_raises(db):
    eng = ProductScoringEngine(db)
    with pytest.raises(ValueError, match="orders_delta must be >= 0"):
        await eng.record_performance(
            product_id="sp_neg",
            ctr=0.0,
            conversion=0.0,
            return_rate=0.0,
            orders_delta=-5,
        )
