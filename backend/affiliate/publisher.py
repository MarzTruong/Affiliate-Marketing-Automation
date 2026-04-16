"""Publisher — đăng ScheduledPost lên các kênh.

Kênh hỗ trợ:
- facebook: Facebook Page API
- wordpress: WordPress REST API
- tiktok: TikTok Content API (draft mode — cần xác nhận thủ công)
"""

import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.automation import ScheduledPost
from backend.models.content import ContentPiece

logger = logging.getLogger(__name__)


async def publish_scheduled_post(db: AsyncSession, post: ScheduledPost) -> None:
    """Đăng 1 ScheduledPost lên kênh tương ứng."""
    content = await db.get(ContentPiece, post.content_id)
    if not content:
        raise ValueError(f"Content {post.content_id} không tồn tại")

    post.status = "publishing"
    await db.flush()

    try:
        external_id = None
        if post.channel == "facebook":
            external_id = await _publish_facebook(content, post.visual_url)
        elif post.channel == "wordpress":
            external_id = await _publish_wordpress(content, post.visual_url)
        elif post.channel == "tiktok":
            external_id = await _publish_tiktok_draft(content, post.visual_url)
        else:
            raise ValueError(f"Kênh không được hỗ trợ: {post.channel}")

        post.status = "published"
        post.published_at = datetime.now(timezone.utc)
        post.external_post_id = external_id

        # Cập nhật content status
        content.status = "published"
        content.published_at = post.published_at

        logger.info(f"✅ Đã đăng lên {post.channel}: {external_id}")

    except Exception as e:
        post.status = "failed"
        post.error_message = str(e)[:500]
        logger.error(f"❌ Lỗi đăng {post.channel}: {e}")
        raise


async def _publish_facebook(content: ContentPiece, visual_url: str | None) -> str:
    """Đăng lên Facebook Page."""
    import httpx

    from backend.config import settings

    if not settings.facebook_access_token or not settings.facebook_page_id:
        raise ValueError("Facebook chưa cấu hình (PAGE_ID, ACCESS_TOKEN)")

    text = _format_post_text(content)

    async with httpx.AsyncClient(timeout=30.0) as client:
        if visual_url and visual_url.startswith("http"):
            # Đăng kèm ảnh
            resp = await client.post(
                f"https://graph.facebook.com/v20.0/{settings.facebook_page_id}/photos",
                params={"access_token": settings.facebook_access_token},
                json={"url": visual_url, "caption": text},
            )
        else:
            # Đăng text only
            resp = await client.post(
                f"https://graph.facebook.com/v20.0/{settings.facebook_page_id}/feed",
                params={"access_token": settings.facebook_access_token},
                json={"message": text},
            )

        resp.raise_for_status()
        data = resp.json()
        return data.get("id", "unknown")


async def _publish_wordpress(content: ContentPiece, visual_url: str | None) -> str:
    """Đăng lên WordPress qua REST API."""
    from base64 import b64encode

    import httpx

    from backend.config import settings

    if not settings.wordpress_site_url:
        raise ValueError("WordPress chưa cấu hình (SITE_URL, USERNAME, APP_PASSWORD)")

    credentials = b64encode(
        f"{settings.wordpress_username}:{settings.wordpress_app_password}".encode()
    ).decode()

    title = content.title or content.body[:80]
    body = content.body
    if visual_url and visual_url.startswith("http"):
        body = f'<img src="{visual_url}" alt="{title}" />\n\n' + body

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{settings.wordpress_site_url.rstrip('/')}/wp-json/wp/v2/posts",
            headers={"Authorization": f"Basic {credentials}"},
            json={
                "title": title,
                "content": body,
                "status": "publish",
                "categories": [],
                "tags": content.seo_keywords or [],
            },
        )
        resp.raise_for_status()
        return str(resp.json().get("id", "unknown"))


async def _publish_tiktok_draft(content: ContentPiece, visual_url: str | None) -> str:
    """Tạo draft TikTok (cần xác nhận thủ công trong TikTok Studio).

    TikTok Content API chỉ hỗ trợ video — không thể đăng text/ảnh tự động.
    Hệ thống tạo draft + thông báo user qua Telegram để review và đăng.
    """
    from backend.config import settings

    if not settings.tiktok_access_token:
        raise ValueError("TikTok chưa cấu hình ACCESS_TOKEN")

    # TikTok không hỗ trợ direct text posting — lưu draft để user đăng thủ công
    draft_id = f"tiktok_draft_{content.id}"
    logger.info(
        f"TikTok draft tạo: {draft_id}\n"
        f"Caption: {_format_post_text(content)[:200]}\n"
        "→ Vào TikTok Creator Studio để đăng video kèm caption này."
    )

    # Thông báo qua Telegram
    try:
        from backend.reports.telegram_reporter import send_tiktok_draft_alert

        await send_tiktok_draft_alert(content, visual_url)
    except Exception:
        pass

    return draft_id


def _format_post_text(content: ContentPiece) -> str:
    """Format text bài đăng kèm hashtags."""
    text = content.body
    if content.seo_keywords:
        hashtags = " ".join(f"#{kw.replace(' ', '')}" for kw in content.seo_keywords[:8])
        text = f"{text}\n\n{hashtags}"
    return text[:2000]  # Giới hạn Facebook
