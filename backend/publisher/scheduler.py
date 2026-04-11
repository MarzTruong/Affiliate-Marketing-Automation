"""Scheduler for auto-publishing content at specified times."""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db_context
from backend.models.publication import Publication
from backend.publisher.posting_service import publish_content

logger = logging.getLogger(__name__)


async def schedule_publication(
    db: AsyncSession,
    content_id: uuid.UUID,
    channels: list[str],
    scheduled_at: datetime,
) -> list[Publication]:
    """Create scheduled publication records for future publishing."""
    results = []
    for channel in channels:
        pub = Publication(
            id=uuid.uuid4(),
            content_id=content_id,
            platform=channel,
            channel=channel,
            scheduled_at=scheduled_at,
            status="scheduled",
        )
        db.add(pub)
        results.append(pub)

    await db.commit()
    logger.info("Scheduled content %s for %d channels at %s", content_id, len(channels), scheduled_at)
    return results


async def process_scheduled_publications():
    """Process all publications that are due for publishing.

    This function is designed to be called periodically (e.g., every minute)
    by an ARQ worker or a simple asyncio loop.
    """
    now = datetime.now(timezone.utc)

    async with get_db_context() as db:
        stmt = select(Publication).where(
            and_(
                Publication.status == "scheduled",
                Publication.scheduled_at <= now,
            )
        )
        result = await db.execute(stmt)
        pending_pubs = result.scalars().all()

        if not pending_pubs:
            return

        # Group by content_id
        by_content: dict[uuid.UUID, list[str]] = {}
        for pub in pending_pubs:
            by_content.setdefault(pub.content_id, []).append(pub.channel)
            pub.status = "publishing"
        await db.commit()

        for content_id, channels in by_content.items():
            try:
                await publish_content(db, content_id, channels)
            except Exception:
                logger.exception("Failed to process scheduled publication for content %s", content_id)
