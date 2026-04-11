import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from backend.compat import GUID, JSONType
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class SOPTemplate(Base):
    __tablename__ = "sop_templates"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    prompt_template: Mapped[str] = mapped_column(Text, nullable=False)
    variables: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    performance_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    avg_conversion_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    avg_ctr: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<SOPTemplate {self.name}>"


class ABTest(Base):
    __tablename__ = "ab_tests"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("campaigns.id"), nullable=False
    )
    template_a_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("sop_templates.id"), nullable=False
    )
    template_b_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("sop_templates.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default="running")
    sample_size_target: Mapped[int] = mapped_column(Integer, default=100)
    variant_a_conversions: Mapped[int] = mapped_column(Integer, default=0)
    variant_a_impressions: Mapped[int] = mapped_column(Integer, default=0)
    variant_b_conversions: Mapped[int] = mapped_column(Integer, default=0)
    variant_b_impressions: Mapped[int] = mapped_column(Integer, default=0)
    winner: Mapped[str | None] = mapped_column(String(1), nullable=True)
    statistical_significance: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    concluded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<ABTest {self.status} winner={self.winner}>"
