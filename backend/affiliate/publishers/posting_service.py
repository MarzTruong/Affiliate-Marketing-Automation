"""Central posting service that dispatches content to configured publishers."""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import nullslast, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.content import ContentPiece
from backend.models.publication import Publication
from backend.publisher.base import BasePublisher, PublishResult
from backend.publisher.facebook import FacebookPublisher
from backend.publisher.wordpress import WordPressPublisher
from backend.publisher.telegram import TelegramPublisher
from backend.publisher.tiktok import TikTokPublisher

logger = logging.getLogger(__name__)

PUBLISHER_REGISTRY: dict[str, type[BasePublisher]] = {
    "facebook": FacebookPublisher,
    "wordpress": WordPressPublisher,
    "telegram": TelegramPublisher,
    "tiktok": TikTokPublisher,
}


def get_publisher(channel: str, **kwargs) -> BasePublisher:
    """Get a publisher instance by channel name."""
    cls = PUBLISHER_REGISTRY.get(channel)
    if not cls:
        raise ValueError(f"Unknown publish channel: {channel}. Available: {list(PUBLISHER_REGISTRY.keys())}")
    return cls(**kwargs)


async def publish_content(
    db: AsyncSession,
    content_id: uuid.UUID,
    channels: list[str],
    extra_kwargs: dict | None = None,
) -> list[Publication]:
    """Publish a content piece to one or more channels.

    Returns a list of Publication records (one per channel).
    """
    extra_kwargs = extra_kwargs or {}

    content = await db.get(ContentPiece, content_id)
    if not content:
        raise ValueError(f"Content {content_id} not found")

    results: list[Publication] = []

    for channel in channels:
        pub = Publication(
            id=uuid.uuid4(),
            content_id=content_id,
            platform=channel,
            channel=channel,
            status="publishing",
        )
        db.add(pub)
        await db.flush()

        try:
            publisher = get_publisher(channel)
            result: PublishResult = await publisher.publish(
                title=content.title or "",
                body=content.body,
                **extra_kwargs.get(channel, {}),
            )

            if result.success:
                pub.status = "published"
                pub.external_post_id = result.external_post_id
                pub.published_at = datetime.now(timezone.utc)
                content.status = "published"
                content.published_at = datetime.now(timezone.utc)
                logger.info("Published content %s to %s: %s", content_id, channel, result.external_post_id)
            else:
                pub.status = "failed"
                logger.error("Failed to publish content %s to %s: %s", content_id, channel, result.error)
        except Exception as e:
            pub.status = "failed"
            logger.exception("Error publishing content %s to %s: %s", content_id, channel, e)

        results.append(pub)

    await db.commit()
    return results


async def get_publications(
    db: AsyncSession,
    content_id: uuid.UUID | None = None,
    channel: str | None = None,
    status: str | None = None,
) -> list[Publication]:
    """Query publications with optional filters."""
    stmt = select(Publication).order_by(nullslast(Publication.published_at.desc()))
    if content_id:
        stmt = stmt.where(Publication.content_id == content_id)
    if channel:
        stmt = stmt.where(Publication.channel == channel)
    if status:
        stmt = stmt.where(Publication.status == status)
    result = await db.execute(stmt)
    return list(result.scalars().all())
