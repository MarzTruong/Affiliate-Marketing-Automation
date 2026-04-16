"""Notification API endpoints."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.notification import Notification

router = APIRouter()


@router.get("")
async def list_notifications(
    unread_only: bool = False,
    severity: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Danh sách thông báo."""
    stmt = select(Notification).order_by(Notification.created_at.desc()).offset(skip).limit(limit)
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))
    if severity:
        stmt = stmt.where(Notification.severity == severity)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/unread-count")
async def unread_count(db: AsyncSession = Depends(get_db)):
    """Số thông báo chưa đọc."""
    count = await db.scalar(select(func.count()).where(Notification.is_read.is_(False))) or 0
    return {"unread": count}


@router.patch("/{notification_id}/read")
async def mark_read(notification_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Đánh dấu đã đọc."""
    notif = await db.get(Notification, notification_id)
    if notif:
        notif.is_read = True
        await db.commit()
    return {"status": "ok"}


@router.post("/read-all")
async def mark_all_read(db: AsyncSession = Depends(get_db)):
    """Đánh dấu tất cả đã đọc."""
    await db.execute(
        update(Notification).where(Notification.is_read.is_(False)).values(is_read=True)
    )
    await db.commit()
    return {"status": "ok"}
