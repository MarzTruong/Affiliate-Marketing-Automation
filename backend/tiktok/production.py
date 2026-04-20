"""TikTok Studio Production Pipeline — script → audio → video clips.

Flow (Kênh 2 — Real Review, default):
  1. Generate TikTok script via Claude (TIKTOK_SCRIPT_TEMPLATE)
  2. Generate audio narration via ElevenLabs (extract VOICE column)
  3. Generate hook + CTA clips via HeyGen (async parallel)

Flow (Kênh 1 — Faceless AI):
  1. Generate TikTok script via Claude
  1b. Record 3 hook variant candidates for Loop 4 A/B test
  2. Generate audio via Gemini TTS (female Southern VN voice)
  3. Generate 3x5s product clips via Kling AI (fal.ai)

Mỗi bước cập nhật TikTokProject ngay sau khi hoàn thành.
Bước nào lỗi → log + raise (KHÔNG swallow).
"""

import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai_engine.gemini_tts_engine import GeminiTTSConfig, GeminiTTSEngine
from backend.ai_engine.kling_engine import KlingConfig, KlingEngine
from backend.models.tiktok_project import TikTokProject

logger = logging.getLogger(__name__)

# Mapping angle → hướng dẫn bổ sung cho Claude
_ANGLE_HINTS = {
    "pain_point": "Mở đầu bằng vấn đề/nỗi đau thực tế của người dùng trước khi giới thiệu giải pháp.",
    "feature": "Mở đầu bằng tính năng ấn tượng nhất — demo trực tiếp, có số liệu cụ thể.",
    "social_proof": "Mở đầu bằng kết quả thực tế đã đạt được — social proof, before/after.",
}

# All valid hook patterns for A/B test
_HOOK_PATTERNS = [
    "pain_point", "shocking_stat", "question", "social_proof",
    "curiosity", "negative", "comparison", "scarcity",
    "myth_busting", "tutorial",
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
        channel_type: "kenh1_faceless" (Gemini TTS + Kling AI + Hook A/B)
                      or "kenh2_real_review" (ElevenLabs + HeyGen, mặc định).

    Trả về project đã được cập nhật đầy đủ.
    """
    already_has_script = project.status not in ("script_pending",) and project.script_body
    already_has_audio = project.audio_url is not None

    if not already_has_script:
        project = await _step_generate_script(db, project)

    if channel_type == "kenh1_faceless":
        if not already_has_script:
            project = await _step_record_hook_variants(db, project)
        if not already_has_audio:
            project = await _step_generate_audio_gemini(db, project)
        project = await _step_generate_kling_clips(db, project)
    else:
        if not already_has_audio:
            project = await _step_generate_audio(db, project)
        project = await _step_generate_clips(db, project)

    await _notify_telegram(project, channel_type)
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


async def _step_generate_script(db: AsyncSession, project: TikTokProject) -> TikTokProject:
    """Bước 1: Gọi Claude để viết kịch bản TikTok."""
    from jinja2 import Template

    from backend.ai_engine.client import ClaudeClient
    from backend.ai_engine.prompts.templates import _COT_HEADER, TIKTOK_SCRIPT_TEMPLATE

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


async def _step_generate_audio(db: AsyncSession, project: TikTokProject) -> TikTokProject:
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


async def _step_generate_clips(db: AsyncSession, project: TikTokProject) -> TikTokProject:
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


async def _step_record_hook_variants(
    db: AsyncSession, project: TikTokProject
) -> TikTokProject:
    """Bước 1b (Kênh 1): Ghi 3 hook variant candidates cho Loop 4 A/B test.

    Dùng project.angle làm primary pattern, chọn thêm 2 pattern ngẫu nhiên từ _HOOK_PATTERNS.
    """
    import random

    from backend.learning.hook_ab_test import HookABTestEngine

    if not project.script_body:
        logger.warning(f"[Production:{project.id}] No script_body — skipping hook variants")
        return project

    if not project.content_id:
        logger.info(f"[Production:{project.id}] No content_id — skipping hook variants")
        return project

    engine = HookABTestEngine(db)
    primary_pattern = project.angle if project.angle in _HOOK_PATTERNS else "pain_point"
    other_patterns = [p for p in _HOOK_PATTERNS if p != primary_pattern]
    patterns_to_record = [primary_pattern] + random.sample(other_patterns, 2)

    # Extract hook line from script (first non-empty line)
    lines = [line.strip() for line in project.script_body.split("\n") if line.strip()]
    hook_text = lines[0] if lines else project.product_name

    for pattern in patterns_to_record:
        await engine.record_variant(
            content_piece_id=project.content_id,
            hook_text=hook_text,
            pattern_type=pattern,
        )

    logger.info(
        f"[Production:{project.id}] Recorded 3 hook variants: {patterns_to_record}"
    )
    return project


async def _step_generate_audio_gemini(
    db: AsyncSession, project: TikTokProject
) -> TikTokProject:
    """Bước 2 (Kênh 1): Tổng hợp giọng nữ trẻ miền Nam qua Gemini TTS."""
    from backend.config import settings

    logger.info(f"[Production:{project.id}] Bước 2 (Kênh 1) — Gemini TTS")

    if not project.script_body:
        logger.warning(f"[Production:{project.id}] No script_body — skipping Gemini TTS")
        return project

    if not getattr(settings, "gemini_api_key", None):
        logger.info(f"[Production:{project.id}] No GEMINI_API_KEY — skipping Gemini TTS")
        return project

    cfg = GeminiTTSConfig(api_key=settings.gemini_api_key)
    engine = GeminiTTSEngine(cfg)

    # Extract voice text (reuse ElevenLabs helper if available, fallback to raw script)
    try:
        from backend.ai_engine.elevenlabs_engine import extract_voice_text
        voice_text = extract_voice_text(project.script_body)
        if not voice_text:
            voice_text = project.script_body[:500]
    except Exception:
        voice_text = project.script_body[:500]

    try:
        result = await engine.generate(voice_text)
        project.audio_url = result.audio_url
        project.audio_duration_s = result.duration_seconds
        project.audio_ready_at = datetime.utcnow()
        project.status = "audio_ready"
        project.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(project)
        logger.info(f"[Production:{project.id}] Gemini TTS done — {result.audio_url}")
    except Exception as e:
        logger.error(f"[Production:{project.id}] Gemini TTS failed: {e}", exc_info=True)
        raise

    return project


async def _resolve_kling_image(image_url: str, product_name: str) -> str | None:
    """Kiểm tra ảnh ≥300x300. Trả về URL nếu OK, None nếu quá nhỏ."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(image_url, follow_redirects=True)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            if "image" not in content_type:
                logger.warning(f"[Kling] URL không phải ảnh: {content_type}")
                return None

            # Đọc header ảnh để lấy kích thước (không cần Pillow)
            data = resp.content
            width, height = _get_image_dimensions(data)
            if width and height:
                if width < 300 or height < 300:
                    logger.warning(
                        f"[Kling] Ảnh quá nhỏ: {width}x{height}px (cần ≥300x300)"
                    )
                    return None
                logger.info(f"[Kling] Ảnh OK: {width}x{height}px")
            return image_url
    except Exception as e:
        logger.warning(f"[Kling] Không kiểm tra được ảnh: {e} — tiếp tục thử")
        return image_url  # fallback: thử gửi lên Kling, để Kling tự báo lỗi


def _get_image_dimensions(data: bytes) -> tuple[int | None, int | None]:
    """Đọc kích thước ảnh JPEG/PNG từ header bytes — không cần Pillow."""
    if data[:2] == b"\xff\xd8":  # JPEG
        import struct
        i = 2
        while i < len(data):
            if data[i] != 0xff:
                break
            marker = data[i + 1]
            if marker in (0xC0, 0xC1, 0xC2):  # SOF markers
                h = struct.unpack(">H", data[i + 5:i + 7])[0]
                w = struct.unpack(">H", data[i + 7:i + 9])[0]
                return w, h
            length = struct.unpack(">H", data[i + 2:i + 4])[0]
            i += 2 + length
    elif data[:8] == b"\x89PNG\r\n\x1a\n":  # PNG
        import struct
        w = struct.unpack(">I", data[16:20])[0]
        h = struct.unpack(">I", data[20:24])[0]
        return w, h
    elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":  # WebP
        if data[12:16] == b"VP8 ":
            import struct
            w = struct.unpack("<H", data[26:28])[0] & 0x3FFF
            h = struct.unpack("<H", data[28:30])[0] & 0x3FFF
            return w, h
    return None, None


async def _step_generate_kling_clips(
    db: AsyncSession, project: TikTokProject
) -> TikTokProject:
    """Bước 3 (Kênh 1): Tạo 3x5s product clips qua Kling AI (fal.ai)."""
    from backend.config import settings

    logger.info(f"[Production:{project.id}] Bước 3 (Kênh 1) — Kling AI clips")

    if not project.script_body:
        logger.warning(f"[Production:{project.id}] No script_body — skipping Kling clips")
        return project

    fal_key = getattr(settings, "fal_key", None) or getattr(settings, "FAL_KEY", None)
    if not fal_key:
        logger.info(f"[Production:{project.id}] No FAL_KEY — skipping Kling clips")
        return project

    if not project.product_ref_url:
        logger.info(
            f"[Production:{project.id}] No product_ref_url for image — skipping Kling clips"
        )
        return project

    # Kiểm tra kích thước ảnh trước khi gọi Kling (tránh lãng phí credit)
    image_url = await _resolve_kling_image(project.product_ref_url, project.product_name)
    if not image_url:
        logger.warning(
            f"[Production:{project.id}] Không tìm được ảnh đủ kích thước (≥300x300) "
            f"— bỏ qua Kling clips. Cập nhật product_ref_url thủ công để thử lại."
        )
        return project

    cfg = KlingConfig(api_key=fal_key)
    engine = KlingEngine(cfg)

    prompts = [
        f"Product shot of {project.product_name}, slow camera pan, clean background",
        f"Close-up detail of {project.product_name}, smooth zoom in",
        f"Lifestyle shot of {project.product_name}, natural lighting, appealing",
    ]

    clip_urls: list[str] = []
    for prompt in prompts:
        try:
            result = await engine.generate(image_url=image_url, prompt=prompt)
            clip_urls.append(result.video_url)
            logger.info(f"[Production:{project.id}] Kling clip: {result.video_url}")
        except Exception as e:
            err_str = str(e)
            if "300x300" in err_str or "image" in err_str.lower() and "small" in err_str.lower():
                logger.error(
                    f"[Production:{project.id}] Kling từ chối ảnh quá nhỏ: {e} "
                    f"— dừng Kling, không retry."
                )
                break  # dừng loop, không raise, giữ nguyên clips đã có
            logger.error(f"[Production:{project.id}] Kling clip failed: {e}", exc_info=True)
            raise

    if clip_urls:
        project.heygen_hook_url = clip_urls[0]   # reuse existing field for clip 1
        if len(clip_urls) > 1:
            project.heygen_cta_url = clip_urls[1]  # reuse for clip 2
        project.clips_ready_at = datetime.utcnow()
        project.status = "clips_ready"
        project.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(project)

    return project
