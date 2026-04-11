"""Telegram Reporter — gửi báo cáo tự động qua Telegram Bot.

Các loại báo cáo:
- send_daily_report: tóm tắt ngày (22:30 VN)
- send_weekly_report: tóm tắt tuần (thứ 2 07:00 VN)
- send_pipeline_report: kết quả pipeline vừa chạy
- send_fraud_alert: cảnh báo fraud phát hiện
- send_tiktok_draft_alert: nhắc user đăng TikTok thủ công

Format: Markdown v2, dùng emoji để dễ đọc trên mobile.
"""

import logging
from datetime import datetime, timedelta, timezone

import httpx

from backend.config import settings

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org"


async def _send(text: str, parse_mode: str = "HTML") -> bool:
    """Gửi message tới Telegram channel/chat."""
    if not settings.telegram_bot_token or not settings.telegram_channel_id:
        logger.warning("Telegram chưa cấu hình — bỏ qua gửi report")
        return False

    url = f"{TELEGRAM_API}/bot{settings.telegram_bot_token}/sendMessage"
    payload = {
        "chat_id": settings.telegram_channel_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                logger.error(f"Telegram API lỗi {resp.status_code}: {resp.text[:200]}")
                return False
        return True
    except Exception as e:
        logger.error(f"Gửi Telegram thất bại: {e}")
        return False


async def send_daily_report(db) -> None:
    """Báo cáo ngày — gửi lúc 22:30 VN."""
    from sqlalchemy import func, select
    from backend.models.analytics import AnalyticsEvent
    from backend.models.automation import PipelineRun, ScheduledPost

    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)

    # Thống kê hôm nay
    click_result = await db.execute(
        select(func.count()).where(
            AnalyticsEvent.event_type == "click",
            AnalyticsEvent.created_at >= today,
            AnalyticsEvent.created_at < tomorrow,
        )
    )
    clicks = click_result.scalar() or 0

    conv_result = await db.execute(
        select(func.count()).where(
            AnalyticsEvent.event_type == "conversion",
            AnalyticsEvent.created_at >= today,
            AnalyticsEvent.created_at < tomorrow,
        )
    )
    conversions = conv_result.scalar() or 0

    # Bài đã đăng hôm nay
    posts_result = await db.execute(
        select(func.count()).where(
            ScheduledPost.status == "published",
            ScheduledPost.published_at >= today,
            ScheduledPost.published_at < tomorrow,
        )
    )
    posts_published = posts_result.scalar() or 0

    # Pipeline runs hôm nay
    runs_result = await db.execute(
        select(func.count()).where(
            PipelineRun.started_at >= today,
            PipelineRun.started_at < tomorrow,
            PipelineRun.status == "completed",
        )
    )
    pipeline_runs = runs_result.scalar() or 0

    ctr = f"{(conversions / clicks * 100):.1f}%" if clicks > 0 else "0%"
    date_str = datetime.now().strftime("%d/%m/%Y")

    text = (
        f"📊 <b>Báo cáo ngày {date_str}</b>\n"
        f"{'─' * 30}\n\n"
        f"🖱️ Lượt click hôm nay: <b>{clicks:,}</b>\n"
        f"✅ Chuyển đổi: <b>{conversions:,}</b>\n"
        f"📈 Tỷ lệ CTR: <b>{ctr}</b>\n\n"
        f"📝 Bài đã đăng: <b>{posts_published}</b>\n"
        f"🤖 Pipeline chạy: <b>{pipeline_runs}</b>\n\n"
    )

    if clicks == 0 and posts_published == 0:
        text += "💡 <i>Chưa có hoạt động hôm nay. Kiểm tra AutomationRule đã bật chưa?</i>"
    elif conversions > 0:
        text += f"🎉 <i>Tốt lắm! Hôm nay có {conversions} chuyển đổi.</i>"
    else:
        text += "⏳ <i>Chưa có chuyển đổi hôm nay — tiếp tục theo dõi!</i>"

    text += f"\n\n⏰ <i>Cập nhật lúc {datetime.now().strftime('%H:%M')} VN</i>"
    await _send(text)


async def send_weekly_report(db) -> None:
    """Tóm tắt tuần — gửi thứ 2 sáng."""
    from sqlalchemy import func, select
    from backend.models.analytics import AnalyticsEvent
    from backend.models.automation import ScheduledPost, TimeSlotPerformance

    week_start = datetime.now(timezone.utc) - timedelta(days=7)

    clicks_r = await db.execute(
        select(func.count()).where(
            AnalyticsEvent.event_type == "click",
            AnalyticsEvent.created_at >= week_start,
        )
    )
    clicks = clicks_r.scalar() or 0

    conv_r = await db.execute(
        select(func.count()).where(
            AnalyticsEvent.event_type == "conversion",
            AnalyticsEvent.created_at >= week_start,
        )
    )
    conversions = conv_r.scalar() or 0

    posts_r = await db.execute(
        select(func.count()).where(
            ScheduledPost.status == "published",
            ScheduledPost.published_at >= week_start,
        )
    )
    total_posts = posts_r.scalar() or 0

    # Top giờ tốt nhất tuần này
    slots_r = await db.execute(
        select(TimeSlotPerformance)
        .order_by(TimeSlotPerformance.performance_score.desc())
        .limit(3)
    )
    top_slots = slots_r.scalars().all()
    day_names = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]

    slot_text = ""
    if top_slots:
        slot_lines = [
            f"  • {day_names[s.day_of_week]} {s.hour:02d}h ({s.channel}) — "
            f"avg {float(s.avg_clicks):.1f} clicks"
            for s in top_slots
        ]
        slot_text = "\n⏰ <b>Giờ hiệu quả nhất:</b>\n" + "\n".join(slot_lines)

    text = (
        f"📋 <b>Tóm tắt tuần</b>\n"
        f"{'─' * 30}\n\n"
        f"🖱️ Tổng click: <b>{clicks:,}</b>\n"
        f"✅ Chuyển đổi: <b>{conversions:,}</b>\n"
        f"📝 Bài đã đăng: <b>{total_posts}</b>\n"
        f"{slot_text}\n\n"
        f"🔄 <i>Adaptive Scheduler đã cập nhật lịch dựa trên data tuần này.</i>\n"
        f"⏰ <i>{datetime.now().strftime('%H:%M')} thứ 2 — Chúc tuần làm việc hiệu quả!</i>"
    )
    await _send(text)


async def send_pipeline_report(run) -> None:
    """Thông báo kết quả pipeline vừa chạy xong."""
    status_icon = "✅" if run.status == "completed" else "❌"
    duration = ""
    if run.finished_at and run.started_at:
        secs = int((run.finished_at - run.started_at).total_seconds())
        duration = f" ({secs}s)"

    text = (
        f"{status_icon} <b>Pipeline hoàn thành{duration}</b>\n"
        f"{'─' * 25}\n\n"
        f"🔍 SP quét được: <b>{run.products_found}</b>\n"
        f"✅ SP đạt tiêu chí: <b>{run.products_filtered}</b>\n"
        f"📝 Bài đã tạo: <b>{run.content_created}</b>\n"
        f"🖼️ Visual đã tạo: <b>{run.visuals_created}</b>\n"
        f"📅 Lịch đăng: <b>{run.posts_scheduled}</b> bài\n"
    )

    if run.status == "failed" and run.error_log:
        text += f"\n⚠️ Lỗi: <code>{run.error_log[:200]}</code>"

    text += f"\n⏰ <i>{datetime.now().strftime('%H:%M %d/%m/%Y')}</i>"
    await _send(text)


async def send_fraud_alert(event_data: dict) -> None:
    """Cảnh báo phát hiện fraud ngay lập tức."""
    text = (
        f"🚨 <b>CẢNH BÁO FRAUD!</b>\n"
        f"{'─' * 25}\n\n"
        f"Loại: <b>{event_data.get('fraud_type', 'unknown')}</b>\n"
        f"Chiến dịch: <b>{event_data.get('campaign', 'N/A')}</b>\n"
        f"Mức độ: <b>{event_data.get('severity', 'medium').upper()}</b>\n"
        f"Chi tiết: {event_data.get('details', '')}\n\n"
        f"⚡ <i>Kiểm tra ngay trong tab Phân tích!</i>"
    )
    await _send(text)


async def send_tiktok_draft_alert(content, visual_url: str | None) -> None:
    """Nhắc user đăng TikTok thủ công."""
    title = content.title or content.body[:50]
    text = (
        f"🎵 <b>TikTok Draft sẵn sàng</b>\n"
        f"{'─' * 25}\n\n"
        f"📝 Bài: <b>{title}</b>\n\n"
        f"Caption đề xuất:\n<code>{content.body[:300]}</code>\n\n"
        f"{'🖼️ Ảnh: ' + visual_url if visual_url else ''}\n\n"
        f"👉 <i>Vào TikTok Creator Studio, upload video và dùng caption trên.</i>"
    )
    await _send(text)


async def send_custom_message(message: str) -> bool:
    """Gửi message tuỳ chỉnh — dùng từ CBD Agent."""
    return await _send(message)
