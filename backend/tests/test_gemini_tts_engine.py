"""Test GeminiTTSEngine — giọng nữ trẻ miền Nam cho Kênh 1."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.ai_engine.gemini_tts_engine import (
    GeminiTTSAuthError,
    GeminiTTSConfig,
    GeminiTTSEngine,
    GeminiTTSTimeoutError,
    TTSResult,
)


def _make_engine(config: GeminiTTSConfig) -> GeminiTTSEngine:
    """Create engine with mocked genai.Client to avoid real API calls."""
    with patch("backend.ai_engine.gemini_tts_engine.genai") as mock_genai:
        mock_genai.Client.return_value = MagicMock()
        engine = GeminiTTSEngine(config)
    return engine


@pytest.mark.unit
def test_config_default_southern_voice():
    cfg = GeminiTTSConfig(api_key="test")
    assert cfg.voice_name == "Aoede"
    assert "miền Nam" in cfg.style_prompt


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_success_returns_url(tmp_path, monkeypatch):
    cfg = GeminiTTSConfig(api_key="test")

    # Patch _AUDIO_DIR to use tmp_path
    import backend.ai_engine.gemini_tts_engine as mod
    monkeypatch.setattr(mod, "_AUDIO_DIR", tmp_path)

    engine = _make_engine(cfg)

    with patch.object(engine, "_call_api", new=AsyncMock(return_value=b"\x00" * 48000)):
        result = await engine.generate("Xin chào các mẹ bầu!")

    assert isinstance(result, TTSResult)
    assert result.audio_url.startswith("/static/audio/")
    assert result.audio_url.endswith(".wav")
    assert result.duration_seconds > 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_writes_file(tmp_path, monkeypatch):
    cfg = GeminiTTSConfig(api_key="test")

    import backend.ai_engine.gemini_tts_engine as mod
    monkeypatch.setattr(mod, "_AUDIO_DIR", tmp_path)

    engine = _make_engine(cfg)
    fake_bytes = b"\x00" * 9600

    with patch.object(engine, "_call_api", new=AsyncMock(return_value=fake_bytes)):
        result = await engine.generate("Test audio write")

    assert result.audio_path.exists()
    assert result.audio_path.read_bytes() == fake_bytes


@pytest.mark.unit
@pytest.mark.asyncio
async def test_empty_text_raises_value_error():
    cfg = GeminiTTSConfig(api_key="test")
    engine = _make_engine(cfg)

    with pytest.raises(ValueError, match="empty"):
        await engine.generate("")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_whitespace_only_raises_value_error():
    cfg = GeminiTTSConfig(api_key="test")
    engine = _make_engine(cfg)

    with pytest.raises(ValueError, match="empty"):
        await engine.generate("   ")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_auth_error_propagates():
    cfg = GeminiTTSConfig(api_key="bad")
    engine = _make_engine(cfg)

    with patch.object(
        engine, "_call_api", new=AsyncMock(side_effect=GeminiTTSAuthError("401"))
    ):
        with pytest.raises(GeminiTTSAuthError):
            await engine.generate("hello")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_timeout_error_propagates():
    cfg = GeminiTTSConfig(api_key="test")
    engine = _make_engine(cfg)

    with patch.object(
        engine, "_call_api", new=AsyncMock(side_effect=GeminiTTSTimeoutError("timeout"))
    ):
        with pytest.raises(GeminiTTSTimeoutError):
            await engine.generate("Xin chào")


@pytest.mark.unit
def test_config_model_default():
    cfg = GeminiTTSConfig(api_key="test")
    assert cfg.model == "gemini-2.5-flash-preview-tts"


@pytest.mark.unit
def test_config_timeout_default():
    cfg = GeminiTTSConfig(api_key="test")
    assert cfg.timeout_seconds == 60.0
