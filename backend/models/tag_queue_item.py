"""TagQueueItem — video chờ user tag SP lên TikTok."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.compat import GUID
from backend.database import Base


class TagQueueItem(Base):
    __tablename__ = "tag_queue_items"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    video_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("content_pieces.id"), nullable=False, index=True
    )
    tiktok_draft_url: Mapped[str] = mapped_column(String(500), nullable=False)

    product_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    product_name: Mapped[str] = mapped_column(String(300), nullable=False)
    commission_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    tagged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
