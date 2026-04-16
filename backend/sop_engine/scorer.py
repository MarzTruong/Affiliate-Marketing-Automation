"""Template performance scorer.

Calculates a composite score for each SOP template based on real analytics data:
- CTR (click-through rate)
- Conversion rate
- Revenue per impression
- Recency bias (newer data weighted more)
"""

import logging
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.analytics import AnalyticsEvent
from backend.models.content import ContentPiece
from backend.models.sop_template import SOPTemplate

logger = logging.getLogger(__name__)

# Score weights (must sum to 1.0)
W_CTR = 0.25
W_CONVERSION = 0.35
W_REVENUE = 0.25
W_VOLUME = 0.15


def _compute_score(impressions: int, clicks: int, conversions: int, revenue: float) -> Decimal:
    """Compute composite performance score (0-100) from raw metrics."""
    if impressions == 0:
        return Decimal("0.00")

    ctr = clicks / impressions
    conversion_rate = conversions / clicks if clicks > 0 else 0
    rpi = revenue / impressions  # revenue per impression

    ctr_score = min(ctr / 0.10 * 100, 100)  # 10% CTR = perfect
    conv_score = min(conversion_rate / 0.05 * 100, 100)  # 5% conv = perfect
    rpi_score = min(rpi / 1000 * 100, 100)  # 1000 VND/impression = perfect
    vol_score = min(impressions / 1000 * 100, 100)  # 1000 impressions = full credit

    composite = (
        W_CTR * ctr_score + W_CONVERSION * conv_score + W_REVENUE * rpi_score + W_VOLUME * vol_score
    )
    return Decimal(str(round(composite, 2)))


async def score_template(db: AsyncSession, template_id, lookback_days: int = 30) -> Decimal:
    """Calculate a composite performance score (0-100) for a single template."""
    since = date.today() - timedelta(days=lookback_days)

    content_ids_q = select(ContentPiece.id).where(
        ContentPiece.template_id == template_id,
        ContentPiece.created_at >= since,
    )

    row = await db.execute(
        select(
            func.count(case((AnalyticsEvent.event_type == "impression", 1))).label("impressions"),
            func.count(case((AnalyticsEvent.event_type == "click", 1))).label("clicks"),
            func.count(case((AnalyticsEvent.event_type == "conversion", 1))).label("conversions"),
            func.coalesce(
                func.sum(case((AnalyticsEvent.event_type == "revenue", AnalyticsEvent.value))),
                0,
            ).label("revenue"),
        ).where(AnalyticsEvent.content_id.in_(content_ids_q))
    )
    r = row.one()
    return _compute_score(r.impressions, r.clicks, r.conversions, float(r.revenue))


async def score_all_templates(db: AsyncSession, lookback_days: int = 30) -> list[dict]:
    """Re-score all active templates and update the database.

    Uses a single batch query instead of per-template queries (O(1) vs O(N)).
    """
    since = date.today() - timedelta(days=lookback_days)

    result = await db.execute(select(SOPTemplate).where(SOPTemplate.is_active.is_(True)))
    templates = result.scalars().all()
    if not templates:
        return []

    template_ids = [t.id for t in templates]

    # Single query: aggregate all metrics for all templates at once
    stats_rows = await db.execute(
        select(
            ContentPiece.template_id,
            func.count(case((AnalyticsEvent.event_type == "impression", 1))).label("impressions"),
            func.count(case((AnalyticsEvent.event_type == "click", 1))).label("clicks"),
            func.count(case((AnalyticsEvent.event_type == "conversion", 1))).label("conversions"),
            func.coalesce(
                func.sum(case((AnalyticsEvent.event_type == "revenue", AnalyticsEvent.value))),
                0,
            ).label("revenue"),
        )
        .join(AnalyticsEvent, AnalyticsEvent.content_id == ContentPiece.id, isouter=True)
        .where(
            ContentPiece.template_id.in_(template_ids),
            ContentPiece.created_at >= since,
        )
        .group_by(ContentPiece.template_id)
    )
    stats_by_template = {row.template_id: row for row in stats_rows}

    scored = []
    for t in templates:
        row = stats_by_template.get(t.id)
        impressions = row.impressions if row else 0
        clicks = row.clicks if row else 0
        conversions = row.conversions if row else 0
        revenue = float(row.revenue) if row else 0.0

        new_score = _compute_score(impressions, clicks, conversions, revenue)
        t.performance_score = new_score

        if impressions > 0:
            t.avg_ctr = Decimal(str(round(clicks / impressions, 4)))
        if clicks > 0:
            t.avg_conversion_rate = Decimal(str(round(conversions / clicks, 4)))

        scored.append(
            {
                "template_id": str(t.id),
                "name": t.name,
                "score": float(new_score),
                "usage_count": t.usage_count,
            }
        )
        logger.info("Scored template %s (%s): %.2f", t.id, t.name, new_score)

    await db.commit()
    return scored
