"""Adaptive Scheduler — tự học giờ đăng bài tốt nhất dựa trên hiệu suất thực tế.

Logic:
- Sau mỗi bài đăng có kết quả (clicks, conversions), cập nhật TimeSlotPerformance
- Hàng tuần: re-rank các khung giờ, cập nhật lịch chạy AutomationRule
- Epsilon-greedy: 90% dùng giờ tốt nhất, 10% thử giờ mới (khám phá)
- Claude API đọc trend hàng tuần, đưa ra gợi ý điều chỉnh chiến lược
"""

import random
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.automation import AutomationRule, ScheduledPost, TimeSlotPerformance

# Trọng số tính performance_score
WEIGHT_CONVERSION = 10.0
WEIGHT_CLICK = 1.0
WEIGHT_REACH = 0.1

# Epsilon-greedy: tỷ lệ thử giờ mới
EXPLORATION_RATE = 0.10

# Exponential moving average — data gần đây được trọng số cao hơn
EMA_ALPHA = 0.3  # 0.3 = 30% data mới, 70% lịch sử


async def record_post_performance(
    db: AsyncSession,
    scheduled_post_id: str,
    clicks: int,
    conversions: int,
    reach: int,
) -> None:
    """Ghi nhận kết quả thực tế sau khi bài đăng có data.
    Cập nhật TimeSlotPerformance với exponential moving average.
    """
    result = await db.execute(select(ScheduledPost).where(ScheduledPost.id == scheduled_post_id))
    post = result.scalar_one_or_none()
    if not post:
        return

    # Lấy content type
    from backend.models.content import ContentPiece

    content_result = await db.execute(
        select(ContentPiece).where(ContentPiece.id == post.content_id)
    )
    content = content_result.scalar_one_or_none()
    content_type = content.content_type if content else "unknown"

    # Cập nhật post
    post.clicks = clicks
    post.conversions = conversions
    post.reach = reach

    # Tìm hoặc tạo TimeSlotPerformance
    hour = post.scheduled_at.hour
    dow = post.scheduled_at.weekday()

    slot_result = await db.execute(
        select(TimeSlotPerformance).where(
            TimeSlotPerformance.hour == hour,
            TimeSlotPerformance.day_of_week == dow,
            TimeSlotPerformance.channel == post.channel,
            TimeSlotPerformance.content_type == content_type,
        )
    )
    slot = slot_result.scalar_one_or_none()

    if not slot:
        slot = TimeSlotPerformance(
            hour=hour,
            day_of_week=dow,
            channel=post.channel,
            content_type=content_type,
            total_posts=0,
            total_clicks=0,
            total_conversions=0,
            total_reach=0,
            avg_clicks=Decimal("0"),
            avg_conversions=Decimal("0"),
            performance_score=Decimal("0"),
        )
        db.add(slot)

    slot.total_posts += 1
    slot.total_clicks += clicks
    slot.total_conversions += conversions
    slot.total_reach += reach

    # Exponential Moving Average — recent data weighted more
    old_clicks = float(slot.avg_clicks)
    old_conv = float(slot.avg_conversions)
    new_avg_clicks = EMA_ALPHA * clicks + (1 - EMA_ALPHA) * old_clicks
    new_avg_conv = EMA_ALPHA * conversions + (1 - EMA_ALPHA) * old_conv

    slot.avg_clicks = Decimal(str(round(new_avg_clicks, 4)))
    slot.avg_conversions = Decimal(str(round(new_avg_conv, 4)))
    slot.performance_score = Decimal(
        str(
            round(
                new_avg_conv * WEIGHT_CONVERSION
                + new_avg_clicks * WEIGHT_CLICK
                + (reach / max(slot.total_posts, 1)) * WEIGHT_REACH,
                4,
            )
        )
    )

    await db.commit()


async def get_best_slots(
    db: AsyncSession,
    channel: str,
    content_type: str,
    n: int = 3,
    day_of_week: int | None = None,
) -> list[int]:
    """Trả về n giờ tốt nhất cho channel + content_type.

    Áp dụng epsilon-greedy: với xác suất EXPLORATION_RATE,
    trả về 1 giờ ngẫu nhiên trong số các giờ chưa thử nhiều.
    """
    query = select(TimeSlotPerformance).where(
        TimeSlotPerformance.channel == channel,
        TimeSlotPerformance.content_type == content_type,
    )
    if day_of_week is not None:
        query = query.where(TimeSlotPerformance.day_of_week == day_of_week)

    result = await db.execute(query.order_by(TimeSlotPerformance.performance_score.desc()))
    slots = result.scalars().all()

    if not slots:
        # Chưa có data — dùng giờ cao điểm VN mặc định
        return _default_peak_hours()[:n]

    best_hours = [s.hour for s in slots[:n]]

    # Epsilon-greedy: 10% thử giờ mới chưa có trong top
    known_hours = {s.hour for s in slots}
    all_hours = set(range(24))
    unexplored = list(all_hours - known_hours)

    if unexplored and random.random() < EXPLORATION_RATE:
        explore_hour = random.choice(unexplored)
        # Thay thế giờ xếp hạng thấp nhất bằng giờ thử nghiệm
        if best_hours:
            best_hours[-1] = explore_hour
        else:
            best_hours = [explore_hour]

    return best_hours


async def update_rule_schedule(db: AsyncSession, rule: AutomationRule) -> str:
    """Cập nhật cron expression của AutomationRule dựa trên giờ tốt nhất học được.

    Chạy hàng tuần để cập nhật lịch theo thị trường thực tế.
    """
    channels = []
    if rule.publish_channels:
        channels = [ch for ch, enabled in rule.publish_channels.items() if enabled]

    if not channels:
        return rule.cron_expression

    # Lấy giờ tốt nhất cho kênh đầu tiên (đại diện)
    primary_channel = channels[0]
    content_type = "social_post"  # default
    if rule.content_types:
        for ct, enabled in rule.content_types.items():
            if enabled:
                content_type = ct
                break

    best_hours = await get_best_slots(db, primary_channel, content_type, n=3)
    hours_str = ",".join(str(h) for h in sorted(best_hours))
    new_cron = f"0 {hours_str} * * *"

    await db.execute(
        update(AutomationRule)
        .where(AutomationRule.id == rule.id)
        .values(cron_expression=new_cron, updated_at=datetime.utcnow())
    )
    await db.commit()
    return new_cron


async def get_schedule_insights(db: AsyncSession) -> dict:
    """Phân tích tổng hợp để gửi cho Claude API hoặc hiển thị trong dashboard."""
    result = await db.execute(
        select(TimeSlotPerformance).order_by(TimeSlotPerformance.performance_score.desc())
    )
    slots = result.scalars().all()

    if not slots:
        return {"message": "Chưa có đủ dữ liệu. Cần ít nhất 7 ngày đăng bài."}

    day_names = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]

    top_slots = [
        {
            "channel": s.channel,
            "hour": f"{s.hour:02d}:00",
            "day": day_names[s.day_of_week],
            "avg_clicks": float(s.avg_clicks),
            "avg_conversions": float(s.avg_conversions),
            "score": float(s.performance_score),
            "total_posts": s.total_posts,
        }
        for s in slots[:10]
    ]

    return {
        "top_slots": top_slots,
        "total_data_points": len(slots),
        "channels_tracked": list({s.channel for s in slots}),
        "last_updated": slots[0].last_updated.isoformat() if slots else None,
    }


def _default_peak_hours() -> list[int]:
    """Giờ cao điểm mặc định cho thị trường VN."""
    return [12, 20, 22]


def next_scheduled_time(best_hours: list[int]) -> datetime:
    """Tính thời điểm đăng tiếp theo gần nhất từ danh sách giờ tốt."""
    now = datetime.now()
    candidates = []
    for h in best_hours:
        candidate = now.replace(hour=h, minute=0, second=0, microsecond=0)
        if candidate <= now:
            candidate += timedelta(days=1)
        candidates.append(candidate)
    return min(candidates)
