"""Model TagQueueItem — tracks videos awaiting manual TikTok SP tagging."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.compat import GUID
from backend.database import Base


class TagQueueItem(Base):
    __tablename__ = "tag_queue_items"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)

    # ── Video reference ───────────────────────────────────────────────────
    video_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False)
    tiktok_draft_url: Mapped[str] = mapped_column(String(500), nullable=False)

    # ── Product info ──────────────────────────────────────────────────────
    product_id: Mapped[str] = mapped_column(String(200), nullable=False)
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    commission_rate: Mapped[float] = mapped_column(Float, nullable=False)

    # ── Timeline ──────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    tagged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
