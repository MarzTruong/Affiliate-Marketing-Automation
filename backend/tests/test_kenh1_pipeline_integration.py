"""Integration test: Kênh 1 pipeline uses Gemini TTS + Kling + Hook A/B."""
from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from backend.ai_engine.gemini_tts_engine import TTSResult
from backend.ai_engine.kling_engine import KlingResult
from backend.models.hook_variant import HookVariant
from backend.tiktok.production import run_production


# ── Shared fakes ──────────────────────────────────────────────────────────────

_FAKE_TTS_RESULT = TTSResult(
    audio_url="/static/audio/test.wav",
    audio_path=Path("/tmp/test.wav"),
    duration_seconds=15.0,
)

_FAKE_KLING_RESULT = KlingResult(
    video_url="https://cdn.fal.ai/clip1.mp4",
    duration_seconds=5,
    prompt="test prompt",
    image_url="https://example.com/meiji.jpg",
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def kenh1_project(db):
    """A TikTokProject with content_id and script_body set (required for full Kênh 1 run)."""
    from backend.tiktok.studio import create_project

    project = await create_project(
        db,
        product_name="Sữa bột Meiji",
        angle="pain_point",
    )
    # Set required fields that production pipeline expects
    project.content_id = uuid.uuid4()
    project.script_body = (
        "Chị em nào đang đau đầu vì chọn sữa bầu?\n"
        "VOICE: Hôm nay mình review sữa Meiji nhé.\n"
        "CTA: Link trong giỏ TikTok Shop."
    )
    project.product_ref_url = "https://example.com/meiji.jpg"
    await db.commit()
    await db.refresh(project)
    return project


def _mock_tts_engine(fake_result: TTSResult = _FAKE_TTS_RESULT) -> MagicMock:
    """Return a MagicMock GeminiTTSEngine instance with AsyncMock generate."""
    instance = MagicMock()
    instance.generate = AsyncMock(return_value=fake_result)
    return instance


def _mock_kling_engine(fake_result: KlingResult = _FAKE_KLING_RESULT) -> MagicMock:
    """Return a MagicMock KlingEngine instance with AsyncMock generate."""
    instance = MagicMock()
    instance.generate = AsyncMock(return_value=fake_result)
    return instance


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.asyncio
async def test_kenh1_pipeline_uses_gemini_tts(db, kenh1_project):
    """Kênh 1 pipeline calls GeminiTTSEngine.generate, not ElevenLabs."""
    tts_instance = _mock_tts_engine()
    kling_instance = _mock_kling_engine()

    with (
        patch(
            "backend.tiktok.production.GeminiTTSEngine",
            return_value=tts_instance,
        ),
        patch(
            "backend.tiktok.production.KlingEngine",
            return_value=kling_instance,
        ),
        patch(
            "backend.config.settings",
            gemini_api_key="test_gemini_key",
            fal_key="test_fal_key",
        ),
        patch(
            "backend.tiktok.production._step_generate_script",
            new=AsyncMock(return_value=kenh1_project),
        ),
    ):
        result = await run_production(db, kenh1_project, channel_type="kenh1_faceless")

    tts_instance.generate.assert_called_once()
    assert result.audio_url == "/static/audio/test.wav"
    assert result.audio_duration_s == 15.0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_kenh1_pipeline_calls_kling_three_times(db, kenh1_project):
    """Kênh 1 pipeline generates exactly 3 Kling clips."""
    tts_instance = _mock_tts_engine()
    kling_instance = _mock_kling_engine()

    with (
        patch(
            "backend.tiktok.production.GeminiTTSEngine",
            return_value=tts_instance,
        ),
        patch(
            "backend.tiktok.production.KlingEngine",
            return_value=kling_instance,
        ),
        patch(
            "backend.config.settings",
            gemini_api_key="test_gemini_key",
            fal_key="test_fal_key",
        ),
        patch(
            "backend.tiktok.production._step_generate_script",
            new=AsyncMock(return_value=kenh1_project),
        ),
    ):
        await run_production(db, kenh1_project, channel_type="kenh1_faceless")

    assert kling_instance.generate.call_count == 3


@pytest.mark.integration
@pytest.mark.asyncio
async def test_kenh1_records_three_hook_variants(db, kenh1_project):
    """Kênh 1 pipeline creates exactly 3 HookVariant rows in DB."""
    from sqlalchemy import select

    tts_instance = _mock_tts_engine()
    kling_instance = _mock_kling_engine()

    with (
        patch(
            "backend.tiktok.production.GeminiTTSEngine",
            return_value=tts_instance,
        ),
        patch(
            "backend.tiktok.production.KlingEngine",
            return_value=kling_instance,
        ),
        patch(
            "backend.config.settings",
            gemini_api_key="test_gemini_key",
            fal_key="test_fal_key",
        ),
        patch(
            "backend.tiktok.production._step_generate_script",
            new=AsyncMock(return_value=kenh1_project),
        ),
    ):
        await run_production(db, kenh1_project, channel_type="kenh1_faceless")

    stmt = select(HookVariant).where(
        HookVariant.content_piece_id == kenh1_project.content_id
    )
    result = await db.execute(stmt)
    variants = result.scalars().all()
    assert len(variants) == 3


@pytest.mark.integration
@pytest.mark.asyncio
async def test_kenh1_hook_variants_include_primary_pattern(db, kenh1_project):
    """Primary pattern (project.angle) must be one of the 3 recorded variants."""
    from sqlalchemy import select

    tts_instance = _mock_tts_engine()
    kling_instance = _mock_kling_engine()

    with (
        patch(
            "backend.tiktok.production.GeminiTTSEngine",
            return_value=tts_instance,
        ),
        patch(
            "backend.tiktok.production.KlingEngine",
            return_value=kling_instance,
        ),
        patch(
            "backend.config.settings",
            gemini_api_key="test_gemini_key",
            fal_key="test_fal_key",
        ),
        patch(
            "backend.tiktok.production._step_generate_script",
            new=AsyncMock(return_value=kenh1_project),
        ),
    ):
        await run_production(db, kenh1_project, channel_type="kenh1_faceless")

    stmt = select(HookVariant).where(
        HookVariant.content_piece_id == kenh1_project.content_id
    )
    result = await db.execute(stmt)
    variants = result.scalars().all()

    pattern_types = {v.pattern_type for v in variants}
    # project.angle = "pain_point" should be in the set
    assert kenh1_project.angle in pattern_types


@pytest.mark.integration
@pytest.mark.asyncio
async def test_kenh2_pipeline_unchanged(db, kenh1_project):
    """Default channel_type (kenh2_real_review) still calls ElevenLabs + HeyGen steps."""
    with (
        patch(
            "backend.tiktok.production._step_generate_script",
            new=AsyncMock(return_value=kenh1_project),
        ) as mock_script,
        patch(
            "backend.tiktok.production._step_generate_audio",
            new=AsyncMock(return_value=kenh1_project),
        ) as mock_audio,
        patch(
            "backend.tiktok.production._step_generate_clips",
            new=AsyncMock(return_value=kenh1_project),
        ) as mock_clips,
    ):
        result = await run_production(db, kenh1_project)  # default = kenh2_real_review

    mock_audio.assert_called_once()
    mock_clips.assert_called_once()
    assert result is kenh1_project


@pytest.mark.integration
@pytest.mark.asyncio
async def test_kenh1_skips_hook_variants_when_no_content_id(db, kenh1_project):
    """If project.content_id is None, hook variants step is skipped gracefully."""
    from sqlalchemy import select

    kenh1_project.content_id = None
    await db.commit()

    tts_instance = _mock_tts_engine()
    kling_instance = _mock_kling_engine()

    with (
        patch(
            "backend.tiktok.production.GeminiTTSEngine",
            return_value=tts_instance,
        ),
        patch(
            "backend.tiktok.production.KlingEngine",
            return_value=kling_instance,
        ),
        patch(
            "backend.config.settings",
            gemini_api_key="test_gemini_key",
            fal_key="test_fal_key",
        ),
        patch(
            "backend.tiktok.production._step_generate_script",
            new=AsyncMock(return_value=kenh1_project),
        ),
    ):
        result = await run_production(db, kenh1_project, channel_type="kenh1_faceless")

    # No hook variants created
    stmt = select(HookVariant)
    db_result = await db.execute(stmt)
    variants = db_result.scalars().all()
    assert len(variants) == 0

    # Pipeline still continues — TTS should have been called
    tts_instance.generate.assert_called_once()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_kenh1_skips_kling_when_no_product_ref_url(db, kenh1_project):
    """Kling step is skipped when project.product_ref_url is None."""
    kenh1_project.product_ref_url = None
    await db.commit()

    tts_instance = _mock_tts_engine()
    kling_instance = _mock_kling_engine()

    with (
        patch(
            "backend.tiktok.production.GeminiTTSEngine",
            return_value=tts_instance,
        ),
        patch(
            "backend.tiktok.production.KlingEngine",
            return_value=kling_instance,
        ),
        patch(
            "backend.config.settings",
            gemini_api_key="test_gemini_key",
            fal_key="test_fal_key",
        ),
        patch(
            "backend.tiktok.production._step_generate_script",
            new=AsyncMock(return_value=kenh1_project),
        ),
    ):
        result = await run_production(db, kenh1_project, channel_type="kenh1_faceless")

    # Kling engine generate should never be called
    kling_instance.generate.assert_not_called()
    # TTS should still run
    tts_instance.generate.assert_called_once()
