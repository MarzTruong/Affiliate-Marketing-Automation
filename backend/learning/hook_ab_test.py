"""HookABTestEngine — Loop 4: learn which hook patterns win by retention@3s."""
from __future__ import annotations

import uuid
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.hook_variant import HookVariant


class HookABTestEngine:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def record_variant(
        self,
        *,
        content_piece_id: uuid.UUID,
        hook_text: str,
        pattern_type: str,
    ) -> HookVariant:
        """Create and persist a new hook variant."""
        v = HookVariant(
            id=uuid.uuid4(),
            content_piece_id=content_piece_id,
            hook_text=hook_text,
            pattern_type=pattern_type,
            retention_at_3s=None,
            score=0.0,
        )
        self.db.add(v)
        await self.db.commit()
        await self.db.refresh(v)
        return v

    async def ingest_retention(
        self, variant_id: uuid.UUID, retention_at_3s: float
    ) -> None:
        """Update retention metric and compute score. Raises ValueError if not found."""
        v = await self.db.get(HookVariant, variant_id)
        if v is None:
            raise ValueError(f"HookVariant {variant_id} not found")
        v.retention_at_3s = retention_at_3s
        v.score = retention_at_3s * 100.0  # scale to 0-100
        await self.db.commit()

    async def top_patterns(self, limit: int = 3) -> list[tuple[str, float]]:
        """Return top N patterns by average score, descending."""
        stmt = select(HookVariant).where(HookVariant.retention_at_3s.is_not(None))
        result = await self.db.execute(stmt)
        variants = result.scalars().all()

        bucket: dict[str, list[float]] = defaultdict(list)
        for v in variants:
            bucket[v.pattern_type].append(v.score)

        ranked = [
            (pattern, sum(scores) / len(scores))
            for pattern, scores in bucket.items()
        ]
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked[:limit]
