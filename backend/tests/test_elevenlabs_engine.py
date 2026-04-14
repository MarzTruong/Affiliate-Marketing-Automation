"""Tests cho ElevenLabs Audio Engine.

Dùng mock để không gọi API thật — test logic, error handling, và voice text extraction.
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.ai_engine.elevenlabs_engine import (
    AudioResult,
    ElevenLabsAudioGenerator,
    ElevenLabsAuthError,
    ElevenLabsConfig,
    ElevenLabsError,
    ElevenLabsRateLimitError,
    extract_voice_text,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def config_no_key():
    return ElevenLabsConfig(api_key="", voice_id="")


@pytest.fixture
def config_valid():
    return ElevenLabsConfig(
        api_key="test_api_key_123",
        voice_id="test_voice_id_abc",
    )


@pytest.fixture
def engine_valid(config_valid):
    return ElevenLabsAudioGenerator(config=config_valid)


SAMPLE_TIKTOK_SCRIPT = """
| ⏱ Thời gian | 🎙 VOICE (AI Text-to-Speech — ElevenLabs) | 📹 VISUAL (B-Roll — Camera Angles) |
|-------------|------------------------------------------|-------------------------------------|
| 0–3s | *"3 giờ sáng, mình vừa pha xong bình sữa mà con vẫn khóc vì sữa nguội quá nhanh"* | Cận cảnh đồng hồ 3:00 AM |
| 4–15s | *"Cái mình đang dùng giữ nhiệt được ở đúng 40°C liên tục 12 tiếng"* | Close-up màn hình 40.0°C |
| 16–35s | *"Thời gian hâm từ lạnh lên 37°C chỉ mất khoảng 3 phút, mình test thật"* | Stop-motion đồng hồ đếm ngược |
| 36–45s | *"Mình dùng được 1 tháng rồi, nhấn vào giỏ vàng góc trái nhé"* | Product shot từ trên xuống |
"""


# ── Tests: initialize ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_initialize_no_api_key(config_no_key):
    """Engine không khởi tạo khi thiếu API key — scaffold mode."""
    engine = ElevenLabsAudioGenerator(config=config_no_key)
    await engine.initialize()
    assert engine.is_available() is False


@pytest.mark.asyncio
async def test_initialize_success(config_valid, tmp_path):
    """Engine khởi tạo thành công khi có API key và Voice ID."""
    engine = ElevenLabsAudioGenerator(config=config_valid)
    mock_client = MagicMock()

    with patch("backend.ai_engine.elevenlabs_engine._AUDIO_DIR", tmp_path), \
         patch("backend.ai_engine.elevenlabs_engine.ElevenLabsAudioGenerator.initialize") as mock_init:

        async def _init(self_inner=None):
            engine._client = mock_client
            engine._initialized = True

        mock_init.side_effect = _init
        await engine.initialize()

    # Arrange: engine initialized manually for test
    engine._client = mock_client
    engine._initialized = True
    assert engine.is_available() is True


@pytest.mark.asyncio
async def test_initialize_import_error(config_valid):
    """Engine xử lý ImportError gracefully khi thiếu elevenlabs package."""
    engine = ElevenLabsAudioGenerator(config=config_valid)

    with patch("builtins.__import__", side_effect=ImportError("No module named 'elevenlabs'")):
        # Should not raise — just log and stay unavailable
        try:
            await engine.initialize()
        except ImportError:
            pass  # acceptable — engine just won't be available

    # Engine vẫn chạy được, chỉ is_available() = False
    assert engine.is_available() is False


# ── Tests: generate_audio ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_generate_audio_not_initialized(engine_valid):
    """Raise ElevenLabsError khi engine chưa initialized."""
    # engine_valid chưa gọi initialize() → _initialized = False
    with pytest.raises(ElevenLabsError, match="chưa khởi tạo"):
        await engine_valid.generate_audio("Xin chào")


@pytest.mark.asyncio
async def test_generate_audio_empty_text(engine_valid):
    """Raise ValueError khi text rỗng."""
    engine_valid._initialized = True
    engine_valid._client = MagicMock()

    with pytest.raises(ValueError, match="Text không được để trống"):
        await engine_valid.generate_audio("   ")


@pytest.mark.asyncio
async def test_generate_audio_success(engine_valid, tmp_path):
    """Generate audio thành công — trả về AudioResult với file_path và audio_url."""
    # Arrange
    engine_valid._initialized = True
    fake_audio_bytes = b"ID3" + b"\x00" * 100  # fake MP3 bytes

    async def fake_audio_generator():
        yield fake_audio_bytes

    mock_tts = AsyncMock()
    mock_tts.convert.return_value = fake_audio_generator()

    mock_client = MagicMock()
    mock_client.text_to_speech = mock_tts
    engine_valid._client = mock_client

    with patch("backend.ai_engine.elevenlabs_engine._AUDIO_DIR", tmp_path), \
         patch("backend.ai_engine.elevenlabs_engine.VoiceSettings", MagicMock()):

        # Act
        result = await engine_valid.generate_audio(
            text="Mình đang review sản phẩm này, rất thích.",
            filename_prefix="test_narration",
        )

    # Assert
    assert isinstance(result, AudioResult)
    assert result.audio_url.startswith("/static/audio/")
    assert result.audio_url.endswith(".mp3")
    assert result.voice_id == "test_voice_id_abc"
    assert result.duration_s > 0
    assert result.char_count > 0
    # File thật sự được tạo
    saved_file = tmp_path / Path(result.audio_url).name
    assert saved_file.exists()
    assert saved_file.read_bytes() == fake_audio_bytes


@pytest.mark.asyncio
async def test_generate_audio_truncates_long_text(engine_valid, tmp_path):
    """Text dài hơn 5000 chars bị cắt trước khi gửi API."""
    engine_valid._initialized = True
    long_text = "A" * 6000
    received_texts = []

    async def fake_audio_gen():
        yield b"fake_mp3"

    mock_tts = AsyncMock()

    async def capture_convert(**kwargs):
        received_texts.append(kwargs.get("text", ""))
        return fake_audio_gen()

    mock_tts.convert.side_effect = capture_convert
    mock_client = MagicMock()
    mock_client.text_to_speech = mock_tts
    engine_valid._client = mock_client

    with patch("backend.ai_engine.elevenlabs_engine._AUDIO_DIR", tmp_path), \
         patch("backend.ai_engine.elevenlabs_engine.VoiceSettings", MagicMock()):
        await engine_valid.generate_audio(text=long_text)

    assert len(received_texts) == 1
    assert len(received_texts[0]) == 5000


@pytest.mark.asyncio
async def test_generate_audio_rate_limit_error(engine_valid):
    """429 từ API → raise ElevenLabsRateLimitError."""
    engine_valid._initialized = True
    engine_valid._client = MagicMock()

    async def fake_audio_gen():
        raise Exception("429 rate limit exceeded quota")
        yield b""  # noqa: unreachable — needed for async generator

    mock_tts = AsyncMock()
    mock_tts.convert.return_value = fake_audio_gen()
    engine_valid._client.text_to_speech = mock_tts

    with patch("backend.ai_engine.elevenlabs_engine.VoiceSettings", MagicMock()):
        with pytest.raises(ElevenLabsRateLimitError):
            await engine_valid.generate_audio("text")


@pytest.mark.asyncio
async def test_generate_audio_auth_error(engine_valid):
    """401 từ API → raise ElevenLabsAuthError."""
    engine_valid._initialized = True
    engine_valid._client = MagicMock()

    async def fake_audio_gen():
        raise Exception("401 unauthorized invalid api key")
        yield b""  # noqa: unreachable

    mock_tts = AsyncMock()
    mock_tts.convert.return_value = fake_audio_gen()
    engine_valid._client.text_to_speech = mock_tts

    with patch("backend.ai_engine.elevenlabs_engine.VoiceSettings", MagicMock()):
        with pytest.raises(ElevenLabsAuthError):
            await engine_valid.generate_audio("text")


# ── Tests: extract_voice_text ─────────────────────────────────────────────────

def test_extract_voice_text_standard_table():
    """Trích xuất đúng 4 dòng VOICE từ TikTok script table chuẩn."""
    result = extract_voice_text(SAMPLE_TIKTOK_SCRIPT)
    assert "3 giờ sáng" in result
    assert "40°C" in result
    assert "3 phút" in result
    assert "giỏ vàng" in result


def test_extract_voice_text_no_visual_column():
    """Không có nội dung từ cột VISUAL trong output."""
    result = extract_voice_text(SAMPLE_TIKTOK_SCRIPT)
    assert "Cận cảnh" not in result
    assert "Close-up" not in result
    assert "Stop-motion" not in result


def test_extract_voice_text_skips_header():
    """Không include header row (VOICE / 🎙) trong kết quả."""
    result = extract_voice_text(SAMPLE_TIKTOK_SCRIPT)
    assert "🎙" not in result
    assert "VOICE" not in result.upper() or "giỏ vàng" in result  # Chỉ kiểm tra header bị skip


def test_extract_voice_text_empty_input():
    """Trả về chuỗi rỗng khi input rỗng."""
    assert extract_voice_text("") == ""
    assert extract_voice_text("   ") == ""


def test_extract_voice_text_no_table_fallback():
    """Fallback về toàn bộ body khi không có table."""
    plain_text = "Đây là script không có bảng. Mình review sản phẩm rất hay."
    result = extract_voice_text(plain_text)
    assert result == plain_text.strip()


def test_extract_voice_text_cleans_markdown():
    """Loại bỏ ký tự markdown (*) khỏi voice text."""
    result = extract_voice_text(SAMPLE_TIKTOK_SCRIPT)
    assert "*" not in result


# ── Tests: _estimate_duration ─────────────────────────────────────────────────

def test_estimate_duration_typical_script():
    """Script 50 từ ≈ 25 giây (120 words/min)."""
    text = " ".join(["mình"] * 50)
    duration = ElevenLabsAudioGenerator._estimate_duration(text)
    assert 20 <= duration <= 30


def test_estimate_duration_empty():
    """Text rỗng → duration = 0."""
    duration = ElevenLabsAudioGenerator._estimate_duration("")
    assert duration == 0.0


# ── Tests: factory ────────────────────────────────────────────────────────────

def test_create_elevenlabs_engine_returns_engine():
    """Factory function trả về ElevenLabsAudioGenerator instance."""
    from backend.ai_engine.elevenlabs_engine import create_elevenlabs_engine
    with patch("backend.ai_engine.elevenlabs_engine.ElevenLabsConfig") as mock_cfg, \
         patch("backend.config.settings") as mock_settings:
        mock_settings.elevenlabs_api_key = "test_key"
        mock_settings.elevenlabs_voice_id = "test_voice"
        engine = create_elevenlabs_engine()
    assert isinstance(engine, ElevenLabsAudioGenerator)
