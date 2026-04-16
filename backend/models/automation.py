"""Models cho hệ thống Automation Pipeline."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.compat import GUID, JSONType
from backend.database import Base


class AutomationRule(Base):
    """Quy tắc tự động hoá: scan SP → tạo content → lên lịch đăng."""

    __tablename__ = "automation_rules"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Nguồn sản phẩm
    platform: Mapped[str] = mapped_column(String(50), nullable=False)  # shopee, accesstrade...
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Tiêu chí lọc sản phẩm
    min_commission_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    min_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    max_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    min_rating: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), nullable=True)
    min_sales: Mapped[int | None] = mapped_column(Integer, nullable=True)
    keywords: Mapped[str | None] = mapped_column(String(500), nullable=True)
    max_products_per_run: Mapped[int] = mapped_column(Integer, default=5)

    # Loại content cần tạo
    content_types: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    # VD: {"product_description": true, "social_post": true, "seo_article": false}

    # Kênh đăng bài
    publish_channels: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    # VD: {"facebook": true, "wordpress": true, "tiktok": false}

    # Visual generation
    generate_visual: Mapped[bool] = mapped_column(Boolean, default=True)
    bannerbear_template_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Lịch chạy (cron expression) - được adaptive scheduler cập nhật tự động
    cron_expression: Mapped[str] = mapped_column(String(100), default="0 12,20,22 * * *")
    # Giờ cao điểm VN mặc định: 12h, 20h, 22h

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    pipeline_runs: Mapped[list["PipelineRun"]] = relationship(back_populates="rule")

    def __repr__(self) -> str:
        return f"<AutomationRule {self.name} [{self.platform}]>"


class PipelineRun(Base):
    """Lịch sử mỗi lần pipeline chạy."""

    __tablename__ = "pipeline_runs"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    rule_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("automation_rules.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default="running")
    # running | completed | failed | partial

    products_found: Mapped[int] = mapped_column(Integer, default=0)
    products_filtered: Mapped[int] = mapped_column(Integer, default=0)
    content_created: Mapped[int] = mapped_column(Integer, default=0)
    visuals_created: Mapped[int] = mapped_column(Integer, default=0)
    posts_scheduled: Mapped[int] = mapped_column(Integer, default=0)

    error_log: Mapped[str | None] = mapped_column(Text, nullable=True)
    run_details: Mapped[dict | None] = mapped_column(JSONType, nullable=True)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    rule: Mapped["AutomationRule"] = relationship(back_populates="pipeline_runs")

    def __repr__(self) -> str:
        return f"<PipelineRun {self.status} products={self.products_filtered}>"


class ScheduledPost(Base):
    """Bài đã được lên lịch đăng."""

    __tablename__ = "scheduled_posts"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    content_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("content_pieces.id"), nullable=False
    )
    pipeline_run_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("pipeline_runs.id"), nullable=True
    )

    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    # facebook | wordpress | tiktok | telegram

    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="scheduled")
    # scheduled | published | failed | cancelled

    visual_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    external_post_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Hiệu suất thực tế (cập nhật sau khi đăng)
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    conversions: Mapped[int] = mapped_column(Integer, default=0)
    reach: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<ScheduledPost {self.channel} @ {self.scheduled_at} [{self.status}]>"


class TimeSlotPerformance(Base):
    """Hiệu suất theo khung giờ — dữ liệu để Adaptive Scheduler tự học.

    Mỗi record = 1 tổ hợp (hour, day_of_week, channel, content_type).
    Cập nhật sau mỗi lần đăng bài có kết quả thực tế.
    """

    __tablename__ = "time_slot_performance"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)

    hour: Mapped[int] = mapped_column(Integer, nullable=False)  # 0-23
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)  # 0=Mon, 6=Sun
    channel: Mapped[str] = mapped_column(String(50), nullable=False)  # facebook, wordpress...
    content_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # Thống kê tích lũy
    total_posts: Mapped[int] = mapped_column(Integer, default=0)
    total_clicks: Mapped[int] = mapped_column(Integer, default=0)
    total_conversions: Mapped[int] = mapped_column(Integer, default=0)
    total_reach: Mapped[int] = mapped_column(Integer, default=0)

    # Trung bình có trọng số (recent data weighted more)
    avg_clicks: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=0)
    avg_conversions: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=0)
    performance_score: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=0)
    # score = avg_conversions * 10 + avg_clicks * 1 (conversions worth more)

    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return (
            f"<TimeSlot {self.channel} {self.day_of_week}d/{self.hour}h "
            f"score={self.performance_score}>"
        )
