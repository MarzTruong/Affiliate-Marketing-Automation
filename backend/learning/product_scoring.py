"""ProductScoringEngine — Loop 5: track per-product performance + auto-blacklist."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.models.product_score import ProductScore

RETURN_RATE_BLACKLIST_THRESHOLD = 0.25


class ProductScoringEngine:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def record_performance(
        self,
        *,
        product_id: str,
        ctr: float,
        conversion: float,
        return_rate: float,
        orders_delta: int,
    ) -> None:
        """Upsert product stats using EMA. Auto-blacklist if return_rate >= 0.25."""
        row = await self.db.get(ProductScore, product_id)
        if row is None:
            row = ProductScore(
                product_id=product_id,
                actual_ctr=ctr,
                actual_conversion=conversion,
                return_rate=return_rate,
                total_orders=orders_delta,
                status="active",
            )
            self.db.add(row)
        else:
            row.actual_ctr = self._ema(row.actual_ctr, ctr)
            row.actual_conversion = self._ema(row.actual_conversion, conversion)
            row.return_rate = self._ema(row.return_rate, return_rate)
            row.total_orders += orders_delta

        if row.return_rate >= RETURN_RATE_BLACKLIST_THRESHOLD:
            row.status = "blacklisted"

        row.last_updated = datetime.now(timezone.utc)
        await self.db.commit()

    @staticmethod
    def _ema(old: float, new: float, alpha: float = 0.3) -> float:
        """Exponential moving average: alpha * new + (1-alpha) * old."""
        return alpha * new + (1 - alpha) * old

    async def list_active(self) -> list[ProductScore]:
        """Return products with status='active'."""
        stmt = select(ProductScore).where(ProductScore.status == "active")
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
