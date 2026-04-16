"""Facebook Webhook Handler.

Nhận engagement events từ Facebook Graph API (likes, comments, shares, reach)
và feed vào Adaptive Scheduler để học giờ đăng tốt nhất.

Luồng:
  Facebook POST → verify signature → parse events → match ScheduledPost
  → record_post_performance() → TimeSlotPerformance updated
"""

import hashlib
import hmac
import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.affiliate.adaptive_scheduler import record_post_performance
from backend.config import settings
from backend.database import get_db
from backend.models.automation import ScheduledPost

logger = logging.getLogger(__name__)

router = APIRouter()


def _verify_facebook_signature(body: bytes, signature_header: str | None, secret: str) -> bool:
    """Xác minh chữ ký X-Hub-Signature-256 từ Facebook.

    Facebook gửi: sha256=<hex_digest>
    Ta tính lại HMAC-SHA256 với webhook secret và so sánh.
    """
    if not signature_header or not secret:
        return False
    if not signature_header.startswith("sha256="):
        return False
    received = signature_header[len("sha256=") :]
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return secrets.compare_digest(expected, received)


def _map_fb_event_to_metrics(change: dict) -> tuple[int, int, int]:
    """Chuyển đổi Facebook engagement event sang (clicks, conversions, reach).

    Facebook webhook change value có thể chứa:
    - reactions/likes → clicks += count
    - comments → clicks += count
    - shares → conversions += count (chia sẻ = hành động mạnh hơn)
    - impressions/reach → reach = count
    """
    value = change.get("value", {})
    field = change.get("field", "")

    clicks = 0
    conversions = 0
    reach = 0

    if field in ("reactions", "likes"):
        clicks += int(value.get("count", value.get("like_count", 0)))
    elif field == "comments":
        clicks += int(value.get("count", value.get("comment_count", 0)))
    elif field == "shares":
        conversions += int(value.get("count", value.get("share_count", 0)))
    elif field in ("impressions", "reach"):
        reach += int(value.get("value", value.get("count", 0)))
    elif field == "post_impressions":
        reach += int(value.get("value", 0))

    return clicks, conversions, reach


@router.get("/facebook")
async def facebook_webhook_verify(request: Request):
    """GET /webhooks/facebook — Facebook hub verification challenge.

    Facebook gọi endpoint này khi đăng ký webhook để xác minh server.
    Ta trả về hub.challenge nếu hub.verify_token khớp.
    """
    params = dict(request.query_params)
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    verify_token = settings.facebook_webhook_verify_token
    if mode == "subscribe" and token == verify_token:
        logger.info("[Webhook] Facebook verification thành công.")
        from fastapi.responses import PlainTextResponse

        return PlainTextResponse(content=challenge or "")

    logger.warning("[Webhook] Facebook verification thất bại — token không khớp.")
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Verification failed")


@router.post("/facebook")
async def facebook_webhook_receive(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """POST /webhooks/facebook — nhận engagement events từ Facebook.

    Facebook gửi payload JSON với danh sách entries và changes.
    Ta verify signature, parse events, match với ScheduledPost rồi
    feed vào Adaptive Scheduler.
    """
    body = await request.body()

    # Verify chữ ký (bỏ qua nếu chưa cấu hình secret — development mode)
    signature = request.headers.get("X-Hub-Signature-256")
    webhook_secret = settings.facebook_webhook_secret
    if webhook_secret:
        if not _verify_facebook_signature(body, signature, webhook_secret):
            logger.warning("[Webhook] Chữ ký Facebook không hợp lệ — từ chối request.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature",
            )

    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"[Webhook] Không parse được JSON payload: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON")

    object_type = payload.get("object")
    if object_type != "page":
        # Chỉ xử lý page events
        return {"status": "ignored", "reason": f"object type '{object_type}' not handled"}

    processed = 0
    skipped = 0

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            external_post_id = value.get("post_id") or value.get("item_id")

            if not external_post_id:
                skipped += 1
                continue

            # Tìm ScheduledPost theo external_post_id
            result = await db.execute(
                select(ScheduledPost).where(ScheduledPost.external_post_id == external_post_id)
            )
            post = result.scalar_one_or_none()
            if not post:
                logger.debug(
                    f"[Webhook] Không tìm thấy ScheduledPost với external_post_id={external_post_id}"
                )
                skipped += 1
                continue

            clicks, conversions, reach = _map_fb_event_to_metrics(change)
            if clicks == 0 and conversions == 0 and reach == 0:
                skipped += 1
                continue

            try:
                await record_post_performance(
                    db=db,
                    scheduled_post_id=str(post.id),
                    clicks=clicks,
                    conversions=conversions,
                    reach=reach,
                )
                processed += 1
                logger.info(
                    f"[Webhook] Cập nhật hiệu suất post {post.id}: "
                    f"clicks={clicks}, conversions={conversions}, reach={reach}"
                )
            except Exception as e:
                logger.error(
                    f"[Webhook] Lỗi khi cập nhật hiệu suất post {post.id}: {e}",
                    exc_info=True,
                )

    return {
        "status": "ok",
        "processed": processed,
        "skipped": skipped,
    }
