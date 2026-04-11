"""Analytics data collector - pulls performance data from platform connectors."""

from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from backend.connectors import get_connector
from backend.database import get_db_context
from backend.models.analytics import AnalyticsEvent
from backend.models.campaign import Campaign


async def collect_platform_data(campaign_id: str, days: int = 1):
    """Pull analytics from platform API and store in analytics_events."""
    async with get_db_context() as db:
        campaign = await db.get(Campaign, campaign_id)
        if not campaign or campaign.status != "active":
            return

        connector = get_connector(campaign.platform)
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        raw_data = await connector.get_performance_data(start_date, end_date)

        for entry in raw_data:
            event = AnalyticsEvent(
                campaign_id=campaign.id,
                event_type=entry.get("type", "click"),
                platform=campaign.platform,
                value=entry.get("value"),
                metadata_json=entry,
            )
            db.add(event)
