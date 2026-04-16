"""Manual publish log — ghi lại lịch sử đăng bài thủ công."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.compat import GUID
from backend.database import Base


class ManualPublishLog(Base):
    __tablename__ = "manual_publish_log"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    content_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("content_pieces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    platform: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # tiktok | facebook | telegram
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    content: Mapped["ContentPiece"] = relationship("ContentPiece")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<ManualPublishLog {self.platform}:{self.content_id}>"
