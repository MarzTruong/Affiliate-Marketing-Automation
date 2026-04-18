"""ProductScore — Loop 5 per-product performance tracking."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class ProductScore(Base):
    __tablename__ = "product_scores"

    product_id: Mapped[str] = mapped_column(String(100), primary_key=True)

    actual_ctr: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    actual_conversion: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    return_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_orders: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active", index=True
    )  # "active" | "blacklisted"

    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
