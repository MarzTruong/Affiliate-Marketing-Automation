"""ProductScoringEngine — Loop 5: score products by CTR, conversion, return rate.

Higher score = better candidate for next video batch.
Score formula: ctr*40 + conversion*50 - return_rate*30 + log1p(orders_delta)*10
"""

from __future__ import annotations

import logging
import math
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.product_score import ProductScore

logger = logging.getLogger(__name__)


class ProductScoringEngine:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def _compute_score(
        ctr: float,
        conversion: float,
        return_rate: float,
        orders_delta: int,
    ) -> float:
        """Composite score formula. Higher is better."""
        return (
            ctr * 40.0
            + conversion * 50.0
            - return_rate * 30.0
            + math.log1p(max(orders_delta, 0)) * 10.0
        )

    async def record_performance(
        self,
        *,
        product_id: str,
        ctr: float,
        conversion: float,
        return_rate: float,
        orders_delta: int,
    ) -> ProductScore:
        """Upsert product score row. Creates new record per observation."""
        if not product_id.strip():
            raise ValueError("product_id must not be empty")

        score = self._compute_score(ctr, conversion, return_rate, orders_delta)

        ps = ProductScore(
            id=uuid.uuid4(),
            product_id=product_id,
            ctr=ctr,
            conversion=conversion,
            return_rate=return_rate,
            orders_delta=orders_delta,
            score=score,
        )
        self.db.add(ps)
        await self.db.commit()
        await self.db.refresh(ps)
        logger.info("ProductScore recorded: product=%s score=%.2f", product_id, score)
        return ps

    async def top_products(self, limit: int = 10) -> list[ProductScore]:
        """Return top N products by latest score, descending."""
        stmt = select(ProductScore).order_by(ProductScore.score.desc()).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
