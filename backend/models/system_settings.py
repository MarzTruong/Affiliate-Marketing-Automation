from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class SystemSettings(Base):
    """Key-value store cho platform credentials và runtime config.

    Thay thế việc ghi đè .env file.
    Chỉ DATABASE_URL và ANTHROPIC_API_KEY vẫn đọc từ .env.
    """

    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<SystemSettings {self.key}>"
