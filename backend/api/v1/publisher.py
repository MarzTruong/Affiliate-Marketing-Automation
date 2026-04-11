"""Publisher API endpoints for auto-posting content."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import get_db
from backend.publisher.posting_service import publish_content, get_publications, PUBLISHER_REGISTRY
from backend.publisher.scheduler import schedule_publication
from backend.schemas.publisher import PublishRequest, ScheduleRequest, PublicationResponse

router = APIRouter()

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
