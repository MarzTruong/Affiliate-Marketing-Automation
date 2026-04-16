"""TikTok Studio Production Pipeline — script → audio → video clips.

Flow:
  1. Generate TikTok script via Claude (TIKTOK_SCRIPT_TEMPLATE)
  2. Generate audio narration via ElevenLabs (extract VOICE column)
  3. Generate hook + CTA clips via HeyGen (async parallel)

Mỗi bước cập nhật TikTokProject ngay sau khi hoàn thành.
Bước nào lỗi → log + raise (KHÔNG swallow).
"""

import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.tiktok_project import TikTokProject

logger = logging.getLogger(__name__)

# Mapping angle → hướng dẫn bổ sung cho Claude
_ANGLE_HINTS = {
    "pain_point": "Mở đầu bằng vấn đề/nỗi đau thực tế của người dùng trước khi giới thiệu giải pháp.",
    "feature": "Mở đầu bằng tính năng ấn tượng nhất — demo trực tiếp, có số liệu cụ thể.",
    "social_proof": "Mở đầu bằng kết quả thực tế đã đạt được — social proof, before/after.",
}


async def run_production(db: AsyncSession, project: TikTokProject) -> TikTokProject:
    """Chạy toàn bộ production pipeline cho 1 TikTokProject.

    Cập nhật project trực tiếp qua 3 bước.
    Trả về project đã được cập nhật đầy đủ.
    """
    project = await _step_generate_script(db, project)
    project = await _step_generate_audio(db, project)
    project = await _step_generate_clips(db, project)
    return project


async def _step_generate_script(
    db: AsyncSession, project: TikTokProject
) -> TikTokProject:
    """Bước 1: Gọi Claude để viết kịch bản TikTok."""
    from backend.ai_engine.client import ClaudeClient
    from backend.ai_engine.prompts.templates import TIKTOK_SCRIPT_TEMPLATE, _COT_HEADER
    from jinja2 import Template

    logger.info(f"[Production:{project.id}] Bước 1 — Tạo script TikTok")

    # Lấy thêm thông tin từ product nếu có
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

    # Thêm angle hint vào mô tả sản phẩm
    if angle_hint:
        variables["description"] = (
            variables["description"] + f"\n\n**Angle yêu cầu:** {angle_hint}"
        ).strip()

    prompt = Template(TIKTOK_SCRIPT_TEMPLATE).render(**variables)

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


async def _step_generate_audio(
    db: AsyncSession, project: TikTokProject
) -> TikTokProject:
    """Bước 2: Tổng hợp giọng đọc từ cột VOICE của script qua ElevenLabs."""
    from backend.ai_engine.elevenlabs_engine import (
        ElevenLabsRateLimitError,
        create_elevenlabs_engine,
        extract_voice_text,
    )

    logger.info(f"[Production:{project.id}] Bước 2 — Tạo audio ElevenLabs")

    if not project.script_body:
        logger.warning(f"[Production:{project.id}] Không có script_body — bỏ qua audio")
        return project

    engine = create_elevenlabs_engine()
    await engine.initialize()

    if not engine.is_available():
        logger.info(f"[Production:{project.id}] ElevenLabs không khả dụng — bỏ qua audio")
        return project

    try:
        voice_text = extract_voice_text(project.script_body)
        if not voice_text:
            logger.warning(f"[Production:{project.id}] Không extract được VOICE text")
            return project

        prefix = f"tiktok_{project.product_name[:20].replace(' ', '_')}"
        result = await engine.generate_audio(text=voice_text, filename_prefix=prefix)

        project.audio_url = result.audio_url
        project.audio_voice_id = result.voice_id
        project.audio_duration_s = result.duration_s
        project.audio_ready_at = datetime.utcnow()
        project.status = "audio_ready"
        project.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(project)

        logger.info(
            f"[Production:{project.id}] Audio sẵn sàng — {result.audio_url} ({result.duration_s:.1f}s)"
        )

    except ElevenLabsRateLimitError as e:
        logger.error(f"[Production:{project.id}] ElevenLabs rate limit: {e}")
        raise
    except Exception as e:
        logger.error(f"[Production:{project.id}] ElevenLabs lỗi: {e}", exc_info=True)
        raise

    return project


async def _step_generate_clips(
    db: AsyncSession, project: TikTokProject
) -> TikTokProject:
    """Bước 3: Tạo hook clip + CTA clip qua HeyGen (song song)."""
    from backend.ai_engine.heygen_engine import (
        HeyGenRateLimitError,
        create_heygen_engine,
    )

    logger.info(f"[Production:{project.id}] Bước 3 — Tạo clips HeyGen")

    if not project.script_body:
        logger.warning(f"[Production:{project.id}] Không có script_body — bỏ qua clips")
        return project

    engine = create_heygen_engine()
    await engine.initialize()

    if not engine.is_available():
        logger.info(f"[Production:{project.id}] HeyGen không khả dụng — bỏ qua clips")
        return project

    try:
        clips = await engine.generate_clips(project.script_body)

        for clip in clips:
            if clip.clip_type == "hook":
                project.heygen_hook_url = clip.video_url
            elif clip.clip_type == "cta":
                project.heygen_cta_url = clip.video_url

        if project.heygen_hook_url or project.heygen_cta_url:
            project.clips_ready_at = datetime.utcnow()
            project.status = "clips_ready"
            project.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(project)

            logger.info(
                f"[Production:{project.id}] Clips sẵn sàng — "
                f"hook={bool(project.heygen_hook_url)}, cta={bool(project.heygen_cta_url)}"
            )

    except HeyGenRateLimitError as e:
        logger.error(f"[Production:{project.id}] HeyGen rate limit: {e}")
        raise
    except Exception as e:
        logger.error(f"[Production:{project.id}] HeyGen lỗi: {e}", exc_info=True)
        raise

    return project
