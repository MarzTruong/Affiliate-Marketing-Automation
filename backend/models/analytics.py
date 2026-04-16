import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.compat import GUID, JSONType
from backend.database import Base


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("campaigns.id"), nullable=True
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("products.id"), nullable=True
    )
    content_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("content_pieces.id"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    platform: Mapped[str | None] = mapped_column(String(50), nullable=True)
    value: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSONType, nullable=True)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_analytics_campaign_time", "campaign_id", "event_time"),
        Index("idx_analytics_type", "event_type"),
    )

    def __repr__(self) -> str:
        return f"<AnalyticsEvent {self.event_type} campaign={self.campaign_id}>"
