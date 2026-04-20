"""Model TikTokProject — theo dõi vòng đời sản xuất video TikTok."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.compat import GUID
from backend.database import Base


class TikTokProject(Base):
    __tablename__ = "tiktok_projects"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)

    # ── Nguồn sản phẩm ────────────────────────────────────────────────────
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("products.id"), nullable=True
    )
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    product_ref_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # ── Nội dung ─────────────────────────────────────────────────────────
    content_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("content_pieces.id"), nullable=True
    )
    script_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    angle: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # pain_point | feature | social_proof
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Audio (ElevenLabs) ───────────────────────────────────────────────
    audio_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    audio_voice_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    audio_duration_s: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Video clips (HeyGen) ─────────────────────────────────────────────
    heygen_hook_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    heygen_cta_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # ── Timeline ─────────────────────────────────────────────────────────
    script_ready_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    audio_ready_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    clips_ready_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    b_roll_filmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    editing_done_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # ── Kênh sản xuất ────────────────────────────────────────────────────
    channel_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default="kenh2_real_review"
    )  # kenh1_faceless | kenh2_real_review

    # ── Status ────────────────────────────────────────────────────────────
    # script_pending → script_ready → audio_ready → clips_ready
    # → b_roll_pending → editing → uploaded → live
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="script_pending")

    # ── Sau khi upload ───────────────────────────────────────────────────
    tiktok_video_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    tiktok_video_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # ── Hiệu suất ────────────────────────────────────────────────────────
    views: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    likes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    comments: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    shares: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
