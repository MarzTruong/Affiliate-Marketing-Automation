"""Test HookABTestEngine — Loop 4 hook pattern learner."""
from __future__ import annotations

import uuid

import pytest

from backend.learning.hook_ab_test import HookABTestEngine
from backend.models.hook_variant import HookVariant


@pytest.mark.unit
@pytest.mark.asyncio
async def test_record_variant_creates_row(db):
    eng = HookABTestEngine(db)
    v = await eng.record_variant(
        content_piece_id=uuid.uuid4(),
        hook_text="Chị em nào đang đau đầu vì mất ngủ...",
        pattern_type="pain_point",
    )
    assert v.id is not None
    assert v.score == 0.0
    assert v.retention_at_3s is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ingest_retention_updates_score(db):
    eng = HookABTestEngine(db)
    v = await eng.record_variant(
        content_piece_id=uuid.uuid4(),
        hook_text="hook",
        pattern_type="question",
    )
    await eng.ingest_retention(v.id, retention_at_3s=0.65)
    refreshed = await db.get(HookVariant, v.id)
    assert refreshed.retention_at_3s == pytest.approx(0.65)
    assert refreshed.score == pytest.approx(65.0)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ingest_retention_not_found_raises(db):
    eng = HookABTestEngine(db)
    with pytest.raises(ValueError, match="not found"):
        await eng.ingest_retention(uuid.uuid4(), 0.5)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_top_patterns_returns_highest_avg_first(db):
    eng = HookABTestEngine(db)
    # pain_point avg = (70+60)/2 = 65, shocking_stat avg = 30
    for pattern, ret in [
        ("pain_point", 0.7),
        ("pain_point", 0.6),
        ("shocking_stat", 0.3),
    ]:
        v = await eng.record_variant(
            content_piece_id=uuid.uuid4(),
            hook_text="h",
            pattern_type=pattern,
        )
        await eng.ingest_retention(v.id, ret)

    top = await eng.top_patterns(limit=2)
    assert top[0][0] == "pain_point"
    assert top[0][1] == pytest.approx(65.0)
