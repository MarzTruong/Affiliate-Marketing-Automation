"""KPI aggregation for dashboard."""

from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.analytics import AnalyticsEvent
from backend.models.content import ContentPiece


async def compute_campaign_kpis(
    db: AsyncSession, campaign_id: UUID, days: int = 30
) -> dict:
    """Compute key performance indicators for a campaign."""
    start = date.today() - timedelta(days=days)
    base_filter = [
        AnalyticsEvent.campaign_id == campaign_id,
        AnalyticsEvent.event_time >= start,
    ]

    clicks = await db.scalar(
        select(func.count()).where(*base_filter, AnalyticsEvent.event_type == "click")
    ) or 0

    conversions = await db.scalar(
        select(func.count()).where(*base_filter, AnalyticsEvent.event_type == "conversion")
    ) or 0

    revenue = await db.scalar(
        select(func.coalesce(func.sum(AnalyticsEvent.value), 0)).where(
            *base_filter, AnalyticsEvent.event_type == "revenue"
        )
    ) or Decimal("0")

    # Claude API cost for this campaign
    api_cost = await db.scalar(
        select(func.coalesce(func.sum(ContentPiece.estimated_cost_usd), 0)).where(
            ContentPiece.campaign_id == campaign_id,
            ContentPiece.created_at >= start,
        )
    ) or Decimal("0")

    conversion_rate = (conversions / clicks * 100) if clicks > 0 else 0
    roas = (float(revenue) / float(api_cost)) if api_cost > 0 else 0

    return {
        "clicks": clicks,
        "conversions": conversions,
        "revenue": float(revenue),
        "api_cost": float(api_cost),
        "conversion_rate": round(conversion_rate, 2),
        "roas": round(roas, 2),
    }
