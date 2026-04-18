"""Model ProductScore — tracks per-product performance metrics for Loop 5 learning."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.compat import GUID
from backend.database import Base


class ProductScore(Base):
    __tablename__ = "product_scores"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)

    # ── Product reference ─────────────────────────────────────────────────
    product_id: Mapped[str] = mapped_column(String(200), nullable=False, index=True)

    # ── Performance metrics ───────────────────────────────────────────────
    ctr: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    conversion: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    return_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    orders_delta: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # ── Composite score (higher = better) ────────────────────────────────
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # ── Timeline ─────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        return f"<ProductScore {self.product_id}:{self.score:.2f}>"
