"""TikTok production pipeline dispatcher.

Routes to channel-specific implementations:
- kenh1_production: Kênh 1 Faceless AI (Gemini TTS + Kling AI + Hook A/B)
- kenh2_production: Kênh 2 Real Review (ElevenLabs + HeyGen)
"""

import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.tiktok_project import TikTokProject
from backend.tiktok.kenh1_production import (
    _get_image_dimensions,
    _resolve_kling_image,
    _upscale_and_upload,
    run_kenh1,
)
from backend.tiktok.kenh2_production import run_kenh2

logger = logging.getLogger(__name__)

# Mapping angle → hướng dẫn bổ sung cho Claude
_ANGLE_HINTS = {
    "pain_point": "Mở đầu bằng vấn đề/nỗi đau thực tế của người dùng trước khi giới thiệu giải pháp.",
    "feature": "Mở đầu bằng tính năng ấn tượng nhất — demo trực tiếp, có số liệu cụ thể.",
    "social_proof": "Mở đầu bằng kết quả thực tế đã đạt được — social proof, before/after.",
}

__all__ = [
    "run_production",
    "_ANGLE_HINTS",
    "_resolve_kling_image",
    "_upscale_and_upload",
    "_get_image_dimensions",
]


async def run_production(
    db: AsyncSession,
    project: TikTokProject,
    channel_type: str = "kenh2_real_review",
) -> TikTokProject:
    """Chạy toàn bộ production pipeline cho 1 TikTokProject.

    Args:
        db: AsyncSession SQLAlchemy.
        project: TikTokProject cần xử lý.
        channel_type: "kenh1_faceless" or "kenh2_real_review" (mặc định).
    """
    if not project.script_body:
        project = await _step_generate_script(db, project)

    if channel_type == "kenh1_faceless":
        project = await run_kenh1(db, project)
    else:
        project = await run_kenh2(db, project)

    await _notify_telegram(project, channel_type)
    return project


async def _step_generate_script(db: AsyncSession, project: TikTokProject) -> TikTokProject:
    """Bước 1 (shared): Gọi Claude để viết kịch bản TikTok."""
    from jinja2 import Template

    from backend.ai_engine.client import ClaudeClient
    from backend.ai_engine.prompts.templates import _COT_HEADER, TIKTOK_SCRIPT_TEMPLATE

    logger.info(f"[Production:{project.id}] Bước 1 — Tạo script TikTok")

    product_info: dict = {}
    if project.product_id:
        from backend.models.product import Product

        product = await db.get(Product, project.product_id)
        if product:
            meta = product.metadata_json or {}
            product_info = {
                "price": str(product.price or ""),
                "category": product.category or "",
                "description": meta.get("description", ""),
                "platform": product.platform or "shopee",
            }

    angle_hint = _ANGLE_HINTS.get(project.angle, "")
    variables = {
        "product_name": project.product_name,
        "price": product_info.get("price", ""),
        "category": product_info.get("category", ""),
        "description": product_info.get("description", ""),
        "platform": product_info.get("platform", "shopee"),
        "few_shot_prefix": "",
        "cot_header": _COT_HEADER,
    }

    if angle_hint:
        variables["description"] = (
            variables["description"] + f"\n\n**Angle yêu cầu:** {angle_hint}"
        ).strip()

    client = ClaudeClient()
    script_body, _ = await client.generate(
        content_type="tiktok_script",
        variables=variables,
        template=TIKTOK_SCRIPT_TEMPLATE,
        model_override="claude-sonnet-4-6",
        max_tokens=1500,
    )

    project.script_body = script_body
    project.script_ready_at = datetime.utcnow()
    project.status = "script_ready"
    project.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(project)

    logger.info(f"[Production:{project.id}] Script sẵn sàng ({len(script_body)} ký tự)")
    return project


async def _notify_telegram(project: TikTokProject, channel_type: str) -> None:
    """Gửi báo cáo hoàn thành pipeline qua Telegram."""
    try:
        from backend.reports.telegram_reporter import send_custom_message

        kenh = "Kenh 1 Faceless AI" if channel_type == "kenh1_faceless" else "Kenh 2 Real Review"
        audio_status = "Co" if project.audio_url else "Khong"
        clips_status = "Co" if project.clips_ready_at else "Khong"

        msg = (
            f"Pipeline hoan thanh!\n\n"
            f"San pham: {project.product_name}\n"
            f"Kenh: {kenh}\n"
            f"Goc: {project.angle}\n"
            f"Script: OK {len(project.script_body or '')} ky tu\n"
            f"Audio: {audio_status}\n"
            f"Clips: {clips_status}\n"
            f"Status: {project.status}\n\n"
            f"Vao TikTok Studio de xem va tai assets."
        )

        await send_custom_message(msg)
        logger.info(f"[Production:{project.id}] Telegram notify da gui")

    except Exception as e:
        logger.warning(f"[Production:{project.id}] Telegram notify that bai (non-critical): {e}")
