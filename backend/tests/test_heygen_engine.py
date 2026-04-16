"""Tests cho HeyGen Video Engine.

Dùng mock httpx để không gọi API thật — test submit, polling, error handling,
script extraction, và factory function.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.ai_engine.heygen_engine import (
    ClipJob,
    ClipResult,
    HeyGenAuthError,
    HeyGenConfig,
    HeyGenError,
    HeyGenRateLimitError,
    HeyGenRenderError,
    HeyGenTimeoutError,
    HeyGenVideoGenerator,
    create_heygen_engine,
    extract_script_parts,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def config_no_key():
    return HeyGenConfig(api_key="", avatar_id="", voice_id="")


@pytest.fixture
def config_valid():
    return HeyGenConfig(
        api_key="test_api_key",
        avatar_id="test_avatar_id",
        voice_id="test_voice_id",
    )


@pytest.fixture
def engine_valid(config_valid):
    return HeyGenVideoGenerator(config=config_valid)


@pytest.fixture
def engine_initialized(config_valid):
    engine = HeyGenVideoGenerator(config=config_valid)
    engine._initialized = True
    return engine


SAMPLE_SCRIPT = """
| ⏱ Thời gian | 🎙 VOICE (AI Text-to-Speech — ElevenLabs) | 📹 VISUAL |
|-------------|------------------------------------------|-----------|
| 0–3s | *"3 giờ sáng mình pha sữa mà con khóc vì nguội quá"* | Cận cảnh đồng hồ |
| 4–15s | *"Cái này giữ 40°C liên tục 12 tiếng"* | Close-up màn hình |
| 16–35s | *"Hâm từ lạnh lên 37°C mất 3 phút thôi"* | Stop-motion |
| 36–45s | *"Dùng 1 tháng rồi, nhấn giỏ vàng góc trái nhé"* | Product shot |
"""


# ── Tests: initialize ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_initialize_no_api_key(config_no_key):
    """Scaffold mode khi thiếu API key."""
    engine = HeyGenVideoGenerator(config=config_no_key)
    await engine.initialize()
    assert engine.is_available() is False


@pytest.mark.asyncio
async def test_initialize_no_avatar_id():
    """Scaffold mode khi thiếu avatar ID."""
    config = HeyGenConfig(api_key="key", avatar_id="", voice_id="voice")
    engine = HeyGenVideoGenerator(config=config)
    await engine.initialize()
    assert engine.is_available() is False


@pytest.mark.asyncio
async def test_initialize_success(config_valid):
    """Initialize thành công khi API key hợp lệ."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        engine = HeyGenVideoGenerator(config=config_valid)
        await engine.initialize()

    assert engine.is_available() is True


@pytest.mark.asyncio
async def test_initialize_401_stays_unavailable(config_valid):
    """401 khi validate → engine không available."""
    mock_resp = MagicMock()
    mock_resp.status_code = 401

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        engine = HeyGenVideoGenerator(config=config_valid)
        await engine.initialize()

    assert engine.is_available() is False


# ── Tests: submit_clip ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_submit_clip_success(engine_initialized):
    """Submit thành công → trả về ClipJob với video_id."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"data": {"video_id": "vid_abc123"}}

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        job = await engine_initialized.submit_clip("Hook text", "hook")

    assert isinstance(job, ClipJob)
    assert job.video_id == "vid_abc123"
    assert job.clip_type == "hook"


@pytest.mark.asyncio
async def test_submit_clip_empty_text(engine_initialized):
    """Raise ValueError khi text rỗng."""
    with pytest.raises(ValueError):
        await engine_initialized.submit_clip("", "hook")


@pytest.mark.asyncio
async def test_submit_clip_auth_error(engine_initialized):
    """401 → raise HeyGenAuthError."""
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = "Unauthorized"

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        with pytest.raises(HeyGenAuthError):
            await engine_initialized.submit_clip("text", "hook")


@pytest.mark.asyncio
async def test_submit_clip_rate_limit(engine_initialized):
    """429 → raise HeyGenRateLimitError."""
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.text = "Too Many Requests"

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        with pytest.raises(HeyGenRateLimitError):
            await engine_initialized.submit_clip("text", "cta")


@pytest.mark.asyncio
async def test_submit_clip_truncates_long_text(engine_initialized):
    """Text > 5000 chars bị cắt."""
    submitted_payloads = []

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"data": {"video_id": "vid_xyz"}}

    async def capture_post(url, headers, json):
        submitted_payloads.append(json)
        return mock_resp

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = capture_post
        mock_client_cls.return_value = mock_client

        await engine_initialized.submit_clip("A" * 6000, "hook")

    text_sent = submitted_payloads[0]["video_inputs"][0]["voice"]["input_text"]
    assert len(text_sent) == 5000


# ── Tests: wait_for_render ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_wait_for_render_completed_first_poll(engine_initialized):
    """Video completed ngay lần poll đầu → trả về ClipResult."""
    job = ClipJob(video_id="vid_123", clip_type="hook")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": {
            "status": "completed",
            "video_url": "https://cdn.heygen.com/video/test.mp4",
        }
    }

    with (
        patch("httpx.AsyncClient") as mock_client_cls,
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        result = await engine_initialized.wait_for_render(job)

    assert isinstance(result, ClipResult)
    assert result.video_url == "https://cdn.heygen.com/video/test.mp4"
    assert result.clip_type == "hook"


@pytest.mark.asyncio
async def test_wait_for_render_failed_status(engine_initialized):
    """HeyGen trả về 'failed' → raise HeyGenRenderError."""
    job = ClipJob(video_id="vid_fail", clip_type="cta")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"data": {"status": "failed", "error": "avatar_not_found"}}

    with (
        patch("httpx.AsyncClient") as mock_client_cls,
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        with pytest.raises(HeyGenRenderError):
            await engine_initialized.wait_for_render(job)


@pytest.mark.asyncio
async def test_wait_for_render_timeout(engine_initialized):
    """Vượt max_wait_s → raise HeyGenTimeoutError."""
    job = ClipJob(video_id="vid_slow", clip_type="hook")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"data": {"status": "processing"}}

    with (
        patch("httpx.AsyncClient") as mock_client_cls,
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        with pytest.raises(HeyGenTimeoutError):
            # max_wait_s=5, poll_interval=10 → timeout ngay sau lần poll đầu
            await engine_initialized.wait_for_render(job, max_wait_s=5)


# ── Tests: generate_clips ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_generate_clips_not_initialized(engine_valid):
    """Raise HeyGenError khi engine chưa initialized."""
    with pytest.raises(HeyGenError, match="chưa khởi tạo"):
        await engine_valid.generate_clips("any script")


@pytest.mark.asyncio
async def test_generate_clips_success(engine_initialized):
    """generate_clips trả về 2 ClipResult (hook + cta)."""
    hook_job = ClipJob(video_id="vid_hook", clip_type="hook")
    cta_job = ClipJob(video_id="vid_cta", clip_type="cta")
    hook_result = ClipResult("vid_hook", "https://cdn.heygen.com/hook.mp4", "hook", 3)
    cta_result = ClipResult("vid_cta", "https://cdn.heygen.com/cta.mp4", "cta", 10)

    with (
        patch.object(engine_initialized, "submit_clip", new_callable=AsyncMock) as mock_submit,
        patch.object(engine_initialized, "wait_for_render", new_callable=AsyncMock) as mock_wait,
    ):
        mock_submit.side_effect = [hook_job, cta_job]
        mock_wait.side_effect = [hook_result, cta_result]

        results = await engine_initialized.generate_clips(SAMPLE_SCRIPT)

    assert len(results) == 2
    clip_types = {r.clip_type for r in results}
    assert clip_types == {"hook", "cta"}


@pytest.mark.asyncio
async def test_generate_clips_partial_failure(engine_initialized):
    """Một clip lỗi → vẫn trả về clip còn lại (graceful)."""
    hook_job = ClipJob(video_id="vid_hook", clip_type="hook")
    hook_result = ClipResult("vid_hook", "https://cdn.heygen.com/hook.mp4", "hook", 3)

    with (
        patch.object(engine_initialized, "submit_clip", new_callable=AsyncMock) as mock_submit,
        patch.object(engine_initialized, "wait_for_render", new_callable=AsyncMock) as mock_wait,
    ):
        # hook ok, cta submit thất bại
        mock_submit.side_effect = [hook_job, HeyGenError("CTA submit failed")]
        mock_wait.side_effect = [hook_result]

        results = await engine_initialized.generate_clips(SAMPLE_SCRIPT)

    assert len(results) == 1
    assert results[0].clip_type == "hook"


# ── Tests: extract_script_parts ───────────────────────────────────────────────


def test_extract_hook_text():
    """Hook text được extract đúng từ dòng 0–3s."""
    parts = extract_script_parts(SAMPLE_SCRIPT)
    assert "3 giờ sáng" in parts.hook_text
    assert parts.hook_text != ""


def test_extract_cta_text():
    """CTA text được extract đúng từ dòng 36–45s."""
    parts = extract_script_parts(SAMPLE_SCRIPT)
    assert "giỏ vàng" in parts.cta_text
    assert parts.cta_text != ""


def test_extract_no_body_row_in_parts():
    """Body rows (4–35s) không xuất hiện trong hook hay cta."""
    parts = extract_script_parts(SAMPLE_SCRIPT)
    assert "12 tiếng" not in parts.hook_text
    assert "12 tiếng" not in parts.cta_text
    assert "3 phút" not in parts.hook_text
    assert "3 phút" not in parts.cta_text


def test_extract_empty_script():
    """Script rỗng → cả 2 field đều rỗng."""
    parts = extract_script_parts("")
    assert parts.hook_text == ""
    assert parts.cta_text == ""


def test_extract_cleans_markdown():
    """Dấu * bị loại bỏ khỏi text."""
    parts = extract_script_parts(SAMPLE_SCRIPT)
    assert "*" not in parts.hook_text
    assert "*" not in parts.cta_text


def test_extract_skips_header_row():
    """Header row (🎙 VOICE) không được include."""
    parts = extract_script_parts(SAMPLE_SCRIPT)
    assert "🎙" not in parts.hook_text
    assert "VOICE" not in parts.hook_text.upper()


# ── Tests: factory ────────────────────────────────────────────────────────────


def test_create_heygen_engine_returns_engine():
    """Factory trả về HeyGenVideoGenerator instance."""
    with patch("backend.config.settings") as mock_settings:
        mock_settings.heygen_api_key = "key"
        mock_settings.heygen_avatar_id = "avatar"
        mock_settings.heygen_voice_id = "voice"
        engine = create_heygen_engine()
    assert isinstance(engine, HeyGenVideoGenerator)
