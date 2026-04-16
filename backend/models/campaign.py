import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.compat import GUID, JSONType
from backend.database import Base


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    platform_account_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("platform_accounts.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="draft")
    budget_daily: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    target_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    config: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    platform_account: Mapped["PlatformAccount | None"] = relationship(back_populates="campaigns")
    products: Mapped[list["Product"]] = relationship(back_populates="campaign")
    content_pieces: Mapped[list["ContentPiece"]] = relationship(back_populates="campaign")

    def __repr__(self) -> str:
        return f"<Campaign {self.name} [{self.status}]>"
