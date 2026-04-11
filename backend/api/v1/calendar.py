"""REST API cho Content Calendar."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.automation import ScheduledPost

router = APIRouter()


@router.get("")
async def get_calendar(
    start_date: str | None = None,
    end_date: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Lấy tất cả bài đăng trong khoảng thời gian cho Calendar view."""
    if start_date:
        start = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
    else:
        start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)

    if end_date:
        end = datetime.fromisoformat(end_date).replace(tzinfo=timezone.utc)
    else:
        end = start + timedelta(days=30)

    result = await db.execute(
        select(ScheduledPost)
        .where(
            ScheduledPost.scheduled_at >= start,
            ScheduledPost.scheduled_at <= end,
        )
        .order_by(ScheduledPost.scheduled_at)
    )
    posts = result.scalars().all()

    # Load content info
    from backend.models.content import ContentPiece
    calendar_items = []
    for post in posts:
        content = await db.get(ContentPiece, post.content_id)
        calendar_items.append({
            "id": str(post.id),
            "content_id": str(post.content_id),
            "title": content.title if content else "Bài đăng",
            "body_preview": (content.body[:120] + "...") if content and len(content.body) > 120 else (content.body if content else ""),
            "channel": post.channel,
            "scheduled_at": post.scheduled_at.isoformat(),
            "published_at": post.published_at.isoformat() if post.published_at else None,
            "status": post.status,
            "visual_url": post.visual_url,
            "clicks": post.clicks,
            "conversions": post.conversions,
        })

    return calendar_items


@router.get("/week")
async def get_week_calendar(
    week_offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """Lấy lịch theo tuần (week_offset=0 là tuần hiện tại)."""
    now = datetime.now(timezone.utc)
    week_start = (now - timedelta(days=now.weekday()) + timedelta(weeks=week_offset)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    week_end = week_start + timedelta(days=7)

    result = await db.execute(
        select(ScheduledPost)
        .where(
            ScheduledPost.scheduled_at >= week_start,
            ScheduledPost.scheduled_at < week_end,
        )
        .order_by(ScheduledPost.scheduled_at)
    )
    posts = result.scalars().all()

    # Nhóm theo ngày
    days: dict[str, list] = {}
    for i in range(7):
        day = (week_start + timedelta(days=i)).strftime("%Y-%m-%d")
        days[day] = []

    from backend.models.content import ContentPiece
    for post in posts:
        day_key = post.scheduled_at.strftime("%Y-%m-%d")
        content = await db.get(ContentPiece, post.content_id)
        if day_key in days:
            days[day_key].append({
                "id": str(post.id),
                "title": content.title if content else "Bài đăng",
                "channel": post.channel,
                "hour": post.scheduled_at.strftime("%H:%M"),
                "status": post.status,
                "visual_url": post.visual_url,
            })

    return {
        "week_start": week_start.strftime("%Y-%m-%d"),
        "week_end": (week_end - timedelta(days=1)).strftime("%Y-%m-%d"),
        "days": days,
    }
