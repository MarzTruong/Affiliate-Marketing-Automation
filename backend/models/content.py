import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Numeric, String, Text, func
from backend.compat import GUID, JSONType, StringArrayType
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class ContentPiece(Base):
    __tablename__ = "content_pieces"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("products.id"), nullable=True
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("campaigns.id"), nullable=False
    )
    content_type: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    seo_keywords: Mapped[list[str] | None] = mapped_column(StringArrayType, nullable=True)
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("sop_templates.id"), nullable=True
    )
    variant: Mapped[str | None] = mapped_column(String(1), nullable=True)
    claude_model: Mapped[str | None] = mapped_column(String(50), nullable=True)
    token_cost_input: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_cost_output: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    platform_variants: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Audio — sinh bởi ElevenLabs TTS (chỉ có với content_type="tiktok_script")
    audio_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    audio_voice_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    audio_duration_s: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Video clips — sinh bởi HeyGen (chỉ có với content_type="tiktok_script")
    heygen_hook_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    heygen_cta_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    product: Mapped["Product | None"] = relationship(back_populates="content_pieces")
    campaign: Mapped["Campaign"] = relationship(back_populates="content_pieces")

    def __repr__(self) -> str:
        return f"<ContentPiece {self.content_type}:{self.title}>"
