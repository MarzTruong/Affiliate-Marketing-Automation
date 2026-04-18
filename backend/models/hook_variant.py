"""HookVariant — lưu các biến thể hook cho A/B test (Loop 4)."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.compat import GUID
from backend.database import Base


class HookVariant(Base):
    __tablename__ = "hook_variants"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    content_piece_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("content_pieces.id"), nullable=False, index=True
    )
    hook_text: Mapped[str] = mapped_column(String(500), nullable=False)
    pattern_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)

    retention_at_3s: Mapped[float | None] = mapped_column(Float, nullable=True)
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
