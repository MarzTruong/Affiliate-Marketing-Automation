"""AITrainingData — lưu bài viết đã được duyệt làm nguồn Few-Shot Learning.

Mỗi lần user Approve (hoặc chỉnh sửa rồi Approve) một bài từ review queue,
bản text cuối cùng được lưu vào bảng này.

ContentGenerator._load_few_shot_examples() đọc bảng này để inject văn mẫu
vào prompt trước khi gọi Claude API.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.compat import GUID
from backend.database import Base


class AITrainingData(Base):
    __tablename__ = "ai_training_data"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)

    # Phân loại để lọc few-shot đúng ngữ cảnh
    content_type: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True
    )  # social_post | seo_article | product_description | video_script
    product_category: Mapped[str] = mapped_column(
        String(100), nullable=False, default="", index=True
    )  # Điện tử | Thời trang | v.v.
    product_platform: Mapped[str] = mapped_column(
        String(50), nullable=False, default=""
    )  # shopee | accesstrade | v.v.

    # Nội dung cuối cùng (đã được human approve / chỉnh sửa)
    final_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Tín hiệu chất lượng: biết bài được approve thẳng hay qua chỉnh sửa
    quality_signal: Mapped[str] = mapped_column(
        String(30), nullable=False, default="approved"
    )  # "approved" | "edited_then_approved"

    # Truy vết nguồn gốc
    source_content_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), nullable=True
    )  # FK mềm sang content_pieces.id (không enforce để tránh cascade issues)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<AITrainingData {self.content_type}:{self.quality_signal}>"
