"""Kênh 2 (Real Review) production steps: ElevenLabs TTS + HeyGen clips."""

import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.tiktok_project import TikTokProject

logger = logging.getLogger(__name__)


async def run_kenh2(db: AsyncSession, project: TikTokProject) -> TikTokProject:
    """Chạy pipeline Kênh 2: ElevenLabs audio → HeyGen clips."""
    already_has_audio = project.audio_url is not None

    if not already_has_audio:
        project = await _step_generate_audio(db, project)
    project = await _step_generate_clips(db, project)
    return project


async def _step_generate_audio(db: AsyncSession, project: TikTokProject) -> TikTokProject:
    """Bước 2 (Kênh 2): Tổng hợp giọng đọc từ cột VOICE của script qua ElevenLabs."""
    from backend.ai_engine.elevenlabs_engine import (
        ElevenLabsRateLimitError,
        create_elevenlabs_engine,
        extract_voice_text,
    )

    logger.info(f"[Kenh2:{project.id}] Bước 2 — Tạo audio ElevenLabs")

    if not project.script_body:
        logger.warning(f"[Kenh2:{project.id}] Không có script_body — bỏ qua audio")
        return project

    engine = create_elevenlabs_engine()
    await engine.initialize()

    if not engine.is_available():
        logger.info(f"[Kenh2:{project.id}] ElevenLabs không khả dụng — bỏ qua audio")
        return project

    try:
        voice_text = extract_voice_text(project.script_body)
        if not voice_text:
            logger.warning(f"[Kenh2:{project.id}] Không extract được VOICE text")
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
            f"[Kenh2:{project.id}] Audio sẵn sàng — {result.audio_url} ({result.duration_s:.1f}s)"
        )

    except ElevenLabsRateLimitError as e:
        logger.error(f"[Kenh2:{project.id}] ElevenLabs rate limit: {e}")
        raise
    except Exception as e:
        logger.error(f"[Kenh2:{project.id}] ElevenLabs lỗi: {e}", exc_info=True)
        raise

    return project


async def _step_generate_clips(db: AsyncSession, project: TikTokProject) -> TikTokProject:
    """Bước 3 (Kênh 2): Tạo hook clip + CTA clip qua HeyGen (song song)."""
    from backend.ai_engine.heygen_engine import (
        HeyGenRateLimitError,
        create_heygen_engine,
    )

    logger.info(f"[Kenh2:{project.id}] Bước 3 — Tạo clips HeyGen")

    if not project.script_body:
        logger.warning(f"[Kenh2:{project.id}] Không có script_body — bỏ qua clips")
        return project

    engine = create_heygen_engine()
    await engine.initialize()

    if not engine.is_available():
        logger.info(f"[Kenh2:{project.id}] HeyGen không khả dụng — bỏ qua clips")
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
                f"[Kenh2:{project.id}] Clips sẵn sàng — "
                f"hook={bool(project.heygen_hook_url)}, cta={bool(project.heygen_cta_url)}"
            )

    except HeyGenRateLimitError as e:
        logger.error(f"[Kenh2:{project.id}] HeyGen rate limit: {e}")
        raise
    except Exception as e:
        logger.error(f"[Kenh2:{project.id}] HeyGen lỗi: {e}", exc_info=True)
        raise

    return project
