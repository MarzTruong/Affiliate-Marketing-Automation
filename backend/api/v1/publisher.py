"""Publisher API endpoints for auto-posting content."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import get_db
from backend.affiliate.publishers.posting_service import publish_content, get_publications, PUBLISHER_REGISTRY
from backend.affiliate.publishers.scheduler import schedule_publication
from backend.schemas.publisher import PublishRequest, ScheduleRequest, PublicationResponse

router = APIRouter()


class MarkPublishedRequest(BaseModel):
    content_id: UUID
    platform: str
    note: str | None = None


class MarkPublishedResponse(BaseModel):
    id: UUID
    content_id: UUID
    platform: str
    published_at: datetime
    note: str | None

# Credential fields required per channel
_CHANNEL_CREDENTIALS: dict[str, list[str]] = {
    "facebook": ["facebook_page_id", "facebook_access_token"],
    "wordpress": ["wordpress_site_url", "wordpress_username", "wordpress_app_password"],
    "telegram": ["telegram_bot_token"],
    "tiktok": ["tiktok_access_token"],
}


def _check_credentials(channels: list[str]) -> None:
    """Raise HTTPException 422 if any channel is missing API credentials."""
    missing = []
    for ch in channels:
        for field in _CHANNEL_CREDENTIALS.get(ch, []):
            val = getattr(settings, field, "")
            if not val:
                missing.append(f"{ch} ({field})")
    if missing:
        raise HTTPException(
            422,
            f"Chưa cấu hình API cho: {', '.join(missing)}. "
            "Vui lòng điền vào mục Cài đặt → Kết nối nền tảng.",
        )


@router.post("/publish", response_model=list[PublicationResponse])
async def publish_now(req: PublishRequest, db: AsyncSession = Depends(get_db)):
    """Đăng nội dung ngay lập tức lên các kênh đã chọn."""
    for ch in req.channels:
        if ch not in PUBLISHER_REGISTRY:
            raise HTTPException(400, f"Kênh không hỗ trợ: {ch}. Có sẵn: {list(PUBLISHER_REGISTRY.keys())}")
    _check_credentials(req.channels)
    try:
        pubs = await publish_content(db, req.content_id, req.channels, req.extra_kwargs)
        # If all channels failed, surface the error clearly
        if pubs and all(p.status == "failed" for p in pubs):
            raise HTTPException(502, "Đăng bài thất bại trên tất cả kênh. Kiểm tra lại API credentials.")
        return pubs
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"Lỗi khi đăng bài: {str(e)}")


@router.post("/schedule", response_model=list[PublicationResponse])
async def schedule_post(req: ScheduleRequest, db: AsyncSession = Depends(get_db)):
    """Lên lịch đăng nội dung vào thời điểm chỉ định."""
    for ch in req.channels:
        if ch not in PUBLISHER_REGISTRY:
            raise HTTPException(400, f"Kênh không hỗ trợ: {ch}")
    try:
        pubs = await schedule_publication(db, req.content_id, req.channels, req.scheduled_at)
        return pubs
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"Lỗi khi lên lịch: {str(e)}")


@router.get("/publications", response_model=list[PublicationResponse])
async def list_publications(
    content_id: UUID | None = None,
    channel: str | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Danh sách bài đăng với bộ lọc tùy chọn."""
    return await get_publications(db, content_id, channel, status)


@router.get("/channels")
async def list_channels():
    """Danh sách các kênh đăng bài có sẵn."""
    return {"channels": list(PUBLISHER_REGISTRY.keys())}


@router.get("/health")
async def publisher_health():
    """Kiểm tra kết nối tất cả các publisher đã cấu hình."""
    import asyncio

    async def _check(channel: str) -> dict:
        creds = _CHANNEL_CREDENTIALS.get(channel, [])
        configured = all(getattr(settings, f, "") for f in creds)
        if not configured:
            return {"channel": channel, "status": "not_configured"}
        try:
            publisher = PUBLISHER_REGISTRY[channel]()
            ok = await publisher.health_check()
            return {"channel": channel, "status": "ok" if ok else "error"}
        except Exception as e:
            return {"channel": channel, "status": "error", "detail": str(e)}

    results = await asyncio.gather(*[_check(ch) for ch in PUBLISHER_REGISTRY])
    return {"platforms": list(results)}


@router.post("/mark-published", response_model=MarkPublishedResponse)
async def mark_published(req: MarkPublishedRequest, db: AsyncSession = Depends(get_db)):
    """Ghi nhận đã đăng bài thủ công lên một platform."""
    from backend.models.content import ContentPiece
    from backend.models.manual_publish_log import ManualPublishLog

    content = await db.get(ContentPiece, req.content_id)
    if not content:
        raise HTTPException(404, f"Content {req.content_id} không tồn tại")

    valid_platforms = {"tiktok", "facebook", "telegram", "wordpress"}
    if req.platform not in valid_platforms:
        raise HTTPException(422, f"Platform không hợp lệ: {req.platform}. Hợp lệ: {valid_platforms}")

    log = ManualPublishLog(
        content_id=req.content_id,
        platform=req.platform,
        published_at=datetime.now(timezone.utc),
        note=req.note,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)

    return MarkPublishedResponse(
        id=log.id,
        content_id=log.content_id,
        platform=log.platform,
        published_at=log.published_at,
        note=log.note,
    )


@router.get("/manual-logs")
async def list_manual_logs(
    content_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Lịch sử đăng bài thủ công."""
    from sqlalchemy import select
    from backend.models.manual_publish_log import ManualPublishLog

    stmt = select(ManualPublishLog).order_by(ManualPublishLog.published_at.desc())
    if content_id:
        stmt = stmt.where(ManualPublishLog.content_id == content_id)
    result = await db.execute(stmt)
    logs = result.scalars().all()
    return [
        {
            "id": str(log.id),
            "content_id": str(log.content_id),
            "platform": log.platform,
            "published_at": log.published_at.isoformat(),
            "note": log.note,
        }
        for log in logs
    ]
