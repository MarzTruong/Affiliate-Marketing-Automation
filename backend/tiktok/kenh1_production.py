"""Kênh 1 (Faceless AI) production steps: Gemini TTS + Kling AI + Hook A/B."""

import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai_engine.gemini_tts_engine import GeminiTTSConfig, GeminiTTSEngine
from backend.ai_engine.kling_engine import KlingConfig, KlingEngine
from backend.models.tiktok_project import TikTokProject

logger = logging.getLogger(__name__)

_HOOK_PATTERNS = [
    "pain_point", "shocking_stat", "question", "social_proof",
    "curiosity", "negative", "comparison", "scarcity",
    "myth_busting", "tutorial",
]


async def run_kenh1(db: AsyncSession, project: TikTokProject) -> TikTokProject:
    """Chạy pipeline Kênh 1: Hook A/B → Gemini TTS → Kling clips → Compose MP4."""
    already_has_audio = project.audio_url is not None

    if not project.script_body:
        logger.warning(f"[Kenh1:{project.id}] No script_body — stopping pipeline")
        return project

    project = await _step_record_hook_variants(db, project)
    if not already_has_audio:
        project = await _step_generate_audio_gemini(db, project)
    project = await _step_generate_kling_clips(db, project)
    project = await _step_compose_mp4(db, project)
    return project


async def _step_record_hook_variants(
    db: AsyncSession, project: TikTokProject
) -> TikTokProject:
    """Bước 1b (Kênh 1): Ghi 3 hook variant candidates cho Loop 4 A/B test."""
    import random

    from backend.learning.hook_ab_test import HookABTestEngine

    if not project.script_body:
        logger.warning(f"[Kenh1:{project.id}] No script_body — skipping hook variants")
        return project

    if not project.content_id:
        logger.info(f"[Kenh1:{project.id}] No content_id — skipping hook variants")
        return project

    engine = HookABTestEngine(db)
    primary_pattern = project.angle if project.angle in _HOOK_PATTERNS else "pain_point"
    other_patterns = [p for p in _HOOK_PATTERNS if p != primary_pattern]
    patterns_to_record = [primary_pattern] + random.sample(other_patterns, 2)

    lines = [line.strip() for line in project.script_body.split("\n") if line.strip()]
    hook_text = lines[0] if lines else project.product_name

    for pattern in patterns_to_record:
        await engine.record_variant(
            content_piece_id=project.content_id,
            hook_text=hook_text,
            pattern_type=pattern,
        )

    logger.info(f"[Kenh1:{project.id}] Recorded 3 hook variants: {patterns_to_record}")
    return project


async def _step_generate_audio_gemini(
    db: AsyncSession, project: TikTokProject
) -> TikTokProject:
    """Bước 2 (Kênh 1): Tổng hợp giọng nữ trẻ miền Nam qua Gemini TTS."""
    from backend.config import settings

    logger.info(f"[Kenh1:{project.id}] Bước 2 — Gemini TTS")

    if not project.script_body:
        logger.warning(f"[Kenh1:{project.id}] No script_body — skipping Gemini TTS")
        return project

    if not getattr(settings, "gemini_api_key", None):
        logger.info(f"[Kenh1:{project.id}] No GEMINI_API_KEY — skipping Gemini TTS")
        return project

    cfg = GeminiTTSConfig(api_key=settings.gemini_api_key)
    engine = GeminiTTSEngine(cfg)

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
        logger.info(f"[Kenh1:{project.id}] Gemini TTS done — {result.audio_url}")
    except Exception as e:
        logger.error(f"[Kenh1:{project.id}] Gemini TTS failed: {e}", exc_info=True)
        raise

    return project


async def _resolve_kling_image(image_url: str, product_name: str) -> str | None:
    """Chuẩn bị URL ảnh đủ ≥300x300 cho Kling (upscale nếu cần)."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(image_url, follow_redirects=True)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            if "image" not in content_type:
                logger.warning(f"[Kling] URL không phải ảnh: {content_type}")
                return None

            data = resp.content
            width, height = _get_image_dimensions(data)

            if width and height and (width < 300 or height < 300):
                logger.info(f"[Kling] Ảnh {width}x{height}px nhỏ hơn 300px — tự upscale lên 512x512")
                upscaled_url = await _upscale_and_upload(data, image_url, product_name)
                if upscaled_url:
                    return upscaled_url
                logger.warning(
                    f"[Kling] Upscale thất bại — trả URL gốc ({width}x{height}px), fal.ai có thể reject"
                )
                return image_url

            if width and height:
                logger.info(f"[Kling] Ảnh OK: {width}x{height}px — dùng URL gốc")
            else:
                logger.info(f"[Kling] Không đọc được kích thước — dùng URL gốc")
            return image_url

    except Exception as e:
        logger.warning(f"[Kling] Không kiểm tra được ảnh: {e} — tiếp tục thử")
        return image_url


async def _upscale_and_upload(
    image_data: bytes, original_url: str, product_name: str
) -> str | None:
    """Upscale ảnh nhỏ lên ≥512x512 bằng Pillow LANCZOS → upload lên fal.ai CDN."""
    try:
        from io import BytesIO

        import fal_client
        from PIL import Image

        img = Image.open(BytesIO(image_data))
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")

        original_size = img.size
        min_side = min(img.size)
        if min_side < 512:
            scale = 512 / min_side
            new_w = int(img.width * scale)
            new_h = int(img.height * scale)
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        buf = BytesIO()
        img.save(buf, format="JPEG", quality=90)
        buf.seek(0)

        import asyncio
        uploaded_url = await asyncio.to_thread(
            fal_client.upload, buf.getvalue(), "image/jpeg"
        )

        logger.info(
            f"[Kling] Upscale {original_size[0]}x{original_size[1]} → "
            f"{img.size[0]}x{img.size[1]}px → fal.ai CDN: {uploaded_url}"
        )
        return uploaded_url

    except ImportError as e:
        logger.error(f"[Kling] Thiếu Pillow hoặc fal_client: {e}")
        return None
    except Exception as e:
        logger.error(f"[Kling] Upscale/upload thất bại: {e}", exc_info=True)
        return None


def _get_image_dimensions(data: bytes) -> tuple[int | None, int | None]:
    """Đọc kích thước ảnh JPEG/PNG/WebP từ header bytes — không cần Pillow."""
    if data[:2] == b"\xff\xd8":  # JPEG
        import struct
        i = 2
        while i < len(data):
            if data[i] != 0xff:
                break
            marker = data[i + 1]
            if marker in (0xC0, 0xC1, 0xC2):
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

    logger.info(f"[Kenh1:{project.id}] Bước 3 — Kling AI clips")

    if not project.script_body:
        logger.warning(f"[Kenh1:{project.id}] No script_body — skipping Kling clips")
        return project

    fal_key = getattr(settings, "fal_key", None) or getattr(settings, "FAL_KEY", None)
    if not fal_key:
        logger.info(f"[Kenh1:{project.id}] No FAL_KEY — skipping Kling clips")
        return project

    if not project.product_ref_url:
        logger.info(f"[Kenh1:{project.id}] No product_ref_url — skipping Kling clips")
        return project

    image_url = await _resolve_kling_image(project.product_ref_url, project.product_name)
    if not image_url:
        logger.warning(
            f"[Kenh1:{project.id}] Không tìm được ảnh đủ kích thước (≥300x300) "
            f"— bỏ qua Kling clips."
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
            logger.info(f"[Kenh1:{project.id}] Kling clip: {result.video_url}")
        except Exception as e:
            err_str = str(e)
            if "300x300" in err_str or ("image" in err_str.lower() and "small" in err_str.lower()):
                logger.error(f"[Kenh1:{project.id}] Kling từ chối ảnh quá nhỏ: {e} — dừng loop.")
                break
            logger.error(f"[Kenh1:{project.id}] Kling clip failed: {e}", exc_info=True)
            raise

    if clip_urls:
        project.heygen_hook_url = clip_urls[0]
        if len(clip_urls) > 1:
            project.heygen_cta_url = clip_urls[1]
        project.clips_ready_at = datetime.utcnow()
        project.status = "clips_ready"
        project.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(project)

    return project


async def _step_compose_mp4(
    db: AsyncSession, project: TikTokProject
) -> TikTokProject:
    """Bước 4 (Kênh 1): Dựng MP4 cuối từ Kling clips + Gemini TTS audio."""
    from backend.video.composer import ComposeRequest, VideoComposerError, compose_tiktok_video

    logger.info(f"[Kenh1:{project.id}] Bước 4 — Compose MP4")

    clip_urls: list[str] = []
    if project.heygen_hook_url:
        clip_urls.append(project.heygen_hook_url)
    if project.heygen_cta_url:
        clip_urls.append(project.heygen_cta_url)

    if not clip_urls:
        logger.warning(f"[Kenh1:{project.id}] Không có clips — bỏ qua compose MP4")
        return project

    if not project.audio_url:
        logger.warning(f"[Kenh1:{project.id}] Không có audio — bỏ qua compose MP4")
        return project

    hook_text = ""
    if project.script_body:
        lines = [l.strip() for l in project.script_body.split("\n") if l.strip()]
        if lines:
            hook_text = lines[0][:60]

    req = ComposeRequest(
        clip_urls=clip_urls,
        audio_url=project.audio_url,
        hook_text=hook_text,
        product_name=project.product_name,
    )

    try:
        result = await compose_tiktok_video(req)
        project.final_video_url = result.video_url
        project.ready_to_post_at = datetime.utcnow()
        project.status = "ready_to_post"
        project.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(project)

        logger.info(
            f"[Kenh1:{project.id}] MP4 sẵn sàng — {result.video_url} "
            f"({result.duration_s:.1f}s, {result.file_size_bytes // 1024}KB)"
        )

        try:
            from backend.reports.telegram_reporter import send_tiktok_ready_to_post

            caption_text = project.script_body or project.title or project.product_name
            await send_tiktok_ready_to_post(
                project_id=str(project.id),
                product_name=project.product_name,
                video_path=result.video_path,
                caption_text=caption_text,
                affiliate_url=project.product_ref_url,
                duration_s=result.duration_s,
            )
        except Exception as notify_err:
            logger.warning(f"[Kenh1:{project.id}] Telegram notify thất bại (non-fatal): {notify_err}")

    except VideoComposerError as e:
        logger.error(f"[Kenh1:{project.id}] Compose MP4 thất bại: {e}", exc_info=True)
        raise

    return project
