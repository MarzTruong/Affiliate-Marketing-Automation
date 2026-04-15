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


async def _send_document(pdf_bytes: bytes, filename: str, caption: str = "") -> bool:
    """Gửi file PDF tới Telegram channel qua sendDocument API."""
    if not settings.telegram_bot_token or not settings.telegram_channel_id:
        logger.warning("Telegram chưa cấu hình — bỏ qua gửi PDF")
        return False

    url = f"{TELEGRAM_API}/bot{settings.telegram_bot_token}/sendDocument"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                url,
                data={"chat_id": settings.telegram_channel_id, "caption": caption},
                files={"document": (filename, bytes(pdf_bytes), "application/pdf")},
            )
            if resp.status_code != 200:
                logger.error(f"Telegram sendDocument lỗi {resp.status_code}: {resp.text[:200]}")
                return False
        return True
    except Exception as e:
        logger.error(f"Gửi Telegram PDF thất bại: {e}")
        return False


def generate_weekly_pdf(
    clicks: int,
    conversions: int,
    total_posts: int,
    top_slots: list,
    week_start: datetime,
) -> bytearray:
    """Tạo PDF báo cáo tuần với fpdf2 — trả về bytearray.

    Cấu trúc PDF:
    1. Header: tên hệ thống + khoảng thời gian
    2. Bảng tóm tắt: clicks, conversions, posts, CTR
    3. Top 3 time slots hiệu quả nhất
    4. Footer: timestamp tạo
    """
    from fpdf import FPDF  # lazy import — chỉ cần khi gọi hàm này

    week_end = week_start + timedelta(days=7)
    ctr = f"{(conversions / clicks * 100):.1f}%" if clicks > 0 else "0%"
    day_names = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]

    pdf = FPDF()
    pdf.set_margins(15, 15, 15)
    pdf.add_page()

    # ── Header ────────────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, "BAO CAO TUAN - AFFILIATE MARKETING", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(
        0, 8,
        f"Tu {week_start.strftime('%d/%m/%Y')} den {week_end.strftime('%d/%m/%Y')}",
        new_x="LMARGIN", new_y="NEXT", align="C",
    )
    pdf.ln(8)

    # ── Tóm tắt ──────────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 10, "TONG KET TUAN", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(180, 180, 180)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(4)

    col_w = 90
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(col_w, 9, "Chi so", border=1, fill=True, align="C")
    pdf.cell(col_w, 9, "Gia tri", border=1, fill=True, align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 11)
    for label, value in [
        ("Luot click", f"{clicks:,}"),
        ("Chuyen doi", f"{conversions:,}"),
        ("Bai da dang", str(total_posts)),
        ("Ty le CTR", ctr),
    ]:
        pdf.cell(col_w, 9, label, border=1)
        pdf.cell(col_w, 9, value, border=1, align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(8)

    # ── Top time slots ────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 10, "GIO DANG HIEU QUA NHAT", new_x="LMARGIN", new_y="NEXT")
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(4)

    if top_slots:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_fill_color(240, 240, 240)
        for header, width in [("Thu", 30), ("Gio", 30), ("Kenh", 60), ("Avg Clicks", 60)]:
            last = header == "Avg Clicks"
            pdf.cell(
                width, 9, header, border=1, fill=True, align="C",
                new_x="LMARGIN" if last else "RIGHT",
                new_y="NEXT" if last else "TOP",
            )

        pdf.set_font("Helvetica", "", 11)
        for s in top_slots:
            pdf.cell(30, 9, day_names[s.day_of_week], border=1, align="C")
            pdf.cell(30, 9, f"{s.hour:02d}:00", border=1, align="C")
            pdf.cell(60, 9, s.channel, border=1, align="C")
            pdf.cell(
                60, 9, f"{float(s.avg_clicks):.1f}", border=1, align="C",
                new_x="LMARGIN", new_y="NEXT",
            )
    else:
        pdf.set_font("Helvetica", "I", 11)
        pdf.cell(0, 9, "Chua co du lieu time slot.", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(8)

    # ── Footer ────────────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(
        0, 8,
        f"Tao luc: {datetime.now().strftime('%H:%M %d/%m/%Y')} | He thong Affiliate Marketing Automation",
        new_x="LMARGIN", new_y="NEXT", align="C",
    )

    return pdf.output()


async def send_weekly_pdf_report(db) -> None:
    """Tạo PDF báo cáo tuần và gửi qua Telegram (thứ 2 07:05 VN)."""
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

    slots_r = await db.execute(
        select(TimeSlotPerformance)
        .order_by(TimeSlotPerformance.performance_score.desc())
        .limit(3)
    )
    top_slots = slots_r.scalars().all()

    try:
        pdf_bytes = generate_weekly_pdf(
            clicks=clicks,
            conversions=conversions,
            total_posts=total_posts,
            top_slots=top_slots,
            week_start=week_start,
        )
        week_end = week_start + timedelta(days=7)
        filename = f"bao_cao_tuan_{week_end.strftime('%d%m%Y')}.pdf"
        caption = f"Bao cao tuan {week_start.strftime('%d/%m')} - {week_end.strftime('%d/%m/%Y')}"
        await _send_document(pdf_bytes, filename, caption)
        logger.info(f"[PDF] Gửi báo cáo tuần thành công: {filename}")
    except Exception as e:
        logger.error(f"[PDF] Lỗi tạo PDF báo cáo tuần: {e}", exc_info=True)


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


async def send_tiktok_draft_alert(
    content,
    visual_url: str | None,
    audio_url: str | None = None,
    heygen_hook_url: str | None = None,
    heygen_cta_url: str | None = None,
) -> None:
    """Nhắc user đăng TikTok thủ công. Kèm link tải assets nếu có."""
    title = content.title or content.body[:50]

    # Build asset section
    asset_lines: list[str] = []
    if audio_url:
        asset_lines.append(f"🎙 <b>Audio MP3:</b> <a href=\"{audio_url}\">Tải về</a>")
    if heygen_hook_url:
        asset_lines.append(f"🎬 <b>Hook clip:</b> <a href=\"{heygen_hook_url}\">Tải Hook (0–3s)</a>")
    if heygen_cta_url:
        asset_lines.append(f"🎬 <b>CTA clip:</b> <a href=\"{heygen_cta_url}\">Tải CTA (36–45s)</a>")
    if visual_url:
        asset_lines.append(f"🖼️ <b>Ảnh:</b> {visual_url}")

    asset_block = ("\n\n📦 <b>Assets sẵn sàng:</b>\n" + "\n".join(asset_lines)) if asset_lines else ""

    text = (
        f"🎵 <b>TikTok Script sẵn sàng</b>\n"
        f"{'─' * 25}\n\n"
        f"📝 Bài: <b>{title}</b>\n\n"
        f"Kịch bản:\n<code>{content.body[:400]}</code>\n"
        f"{asset_block}\n\n"
        f"👉 <i>Dùng audio MP3 + B-roll tự quay → dựng trong CapCut → upload TikTok.</i>"
    )
    await _send(text)


async def send_custom_message(message: str) -> bool:
    """Gửi message tuỳ chỉnh — dùng từ CBD Agent."""
    return await _send(message)
