"""A/B testing engine for SOP templates.

Creates tests between two templates, tracks performance per variant,
and concludes tests with statistical significance calculation.
"""

import logging
import math
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.sop_template import ABTest, SOPTemplate

logger = logging.getLogger(__name__)


def _z_test_proportion(n_a: int, c_a: int, n_b: int, c_b: int) -> float:
    """Two-proportion z-test. Returns p-value (two-tailed).

    n_a, n_b = sample sizes; c_a, c_b = conversions.
    """
    if n_a == 0 or n_b == 0:
        return 1.0

    p_a = c_a / n_a
    p_b = c_b / n_b
    p_pool = (c_a + c_b) / (n_a + n_b)

    if p_pool == 0 or p_pool == 1:
        return 1.0

    se = math.sqrt(p_pool * (1 - p_pool) * (1 / n_a + 1 / n_b))
    if se == 0:
        return 1.0

    z = abs(p_a - p_b) / se

    # Approximate p-value from z-score (two-tailed)
    p_value = math.erfc(z / math.sqrt(2))
    return p_value


async def create_ab_test(
    db: AsyncSession,
    campaign_id: uuid.UUID,
    template_a_id: uuid.UUID,
    template_b_id: uuid.UUID,
    sample_size_target: int = 100,
) -> ABTest:
    """Create a new A/B test between two templates."""
    # Verify both templates exist
    tmpl_a = await db.get(SOPTemplate, template_a_id)
    tmpl_b = await db.get(SOPTemplate, template_b_id)
    if not tmpl_a or not tmpl_b:
        raise ValueError("One or both templates not found")

    test = ABTest(
        id=uuid.uuid4(),
        campaign_id=campaign_id,
        template_a_id=template_a_id,
        template_b_id=template_b_id,
        sample_size_target=sample_size_target,
        status="running",
    )
    db.add(test)
    await db.commit()
    await db.refresh(test)

    logger.info("Created A/B test %s: %s vs %s", test.id, tmpl_a.name, tmpl_b.name)
    return test


async def record_impression(db: AsyncSession, test_id: uuid.UUID, variant: str) -> None:
    """Record an impression for variant A or B."""
    test = await db.get(ABTest, test_id)
    if not test or test.status != "running":
        return

    if variant == "A":
        test.variant_a_impressions += 1
    elif variant == "B":
        test.variant_b_impressions += 1
    await db.commit()


async def record_conversion(db: AsyncSession, test_id: uuid.UUID, variant: str) -> None:
    """Record a conversion for variant A or B."""
    test = await db.get(ABTest, test_id)
    if not test or test.status != "running":
        return

    if variant == "A":
        test.variant_a_conversions += 1
    elif variant == "B":
        test.variant_b_conversions += 1

    # Auto-conclude if sample size reached
    total = test.variant_a_impressions + test.variant_b_impressions
    if total >= test.sample_size_target:
        await _conclude_test(db, test)
    else:
        await db.commit()


async def _conclude_test(db: AsyncSession, test: ABTest) -> None:
    """Conclude a test by determining the winner."""
    p_value = _z_test_proportion(
        test.variant_a_impressions,
        test.variant_a_conversions,
        test.variant_b_impressions,
        test.variant_b_conversions,
    )

    test.statistical_significance = Decimal(str(round(1 - p_value, 4)))
    test.concluded_at = datetime.now(timezone.utc)

    # Determine winner (significance threshold: 95%)
    if p_value < 0.05:
        rate_a = (
            test.variant_a_conversions / test.variant_a_impressions
            if test.variant_a_impressions > 0
            else 0
        )
        rate_b = (
            test.variant_b_conversions / test.variant_b_impressions
            if test.variant_b_impressions > 0
            else 0
        )
        test.winner = "A" if rate_a >= rate_b else "B"
        test.status = "concluded"

        # Boost winner template score, penalize loser
        winner_id = test.template_a_id if test.winner == "A" else test.template_b_id
        loser_id = test.template_b_id if test.winner == "A" else test.template_a_id

        winner = await db.get(SOPTemplate, winner_id)
        loser = await db.get(SOPTemplate, loser_id)
        if winner:
            winner.performance_score = min(
                winner.performance_score + Decimal("5.00"), Decimal("100.00")
            )
        if loser:
            loser.performance_score = max(
                loser.performance_score - Decimal("3.00"), Decimal("0.00")
            )

        logger.info(
            "A/B test %s concluded: winner=%s (sig=%.2f%%)",
            test.id,
            test.winner,
            float(test.statistical_significance) * 100,
        )
    else:
        test.status = "inconclusive"
        test.winner = None
        logger.info("A/B test %s inconclusive (p=%.4f)", test.id, p_value)

    await db.commit()


async def conclude_test_manually(db: AsyncSession, test_id: uuid.UUID) -> ABTest:
    """Force-conclude an A/B test regardless of sample size."""
    test = await db.get(ABTest, test_id)
    if not test:
        raise ValueError(f"Test {test_id} not found")
    if test.status != "running":
        raise ValueError(f"Test is already {test.status}")

    await _conclude_test(db, test)
    return test


async def get_running_tests(db: AsyncSession, campaign_id: uuid.UUID | None = None) -> list[ABTest]:
    """List running A/B tests, optionally filtered by campaign."""
    stmt = select(ABTest).where(ABTest.status == "running")
    if campaign_id:
        stmt = stmt.where(ABTest.campaign_id == campaign_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def pick_variant(db: AsyncSession, test_id: uuid.UUID) -> str:
    """Pick which variant to show next (round-robin for balance)."""
    test = await db.get(ABTest, test_id)
    if not test or test.status != "running":
        return "A"

    # Pick the variant with fewer impressions; prefer A on tie (deterministic round-robin)
    if test.variant_b_impressions < test.variant_a_impressions:
        return "B"
    return "A"
