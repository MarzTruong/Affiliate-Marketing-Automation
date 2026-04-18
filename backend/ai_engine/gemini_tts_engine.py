"""GeminiTTSEngine — Gemini 2.5 Flash TTS Vietnamese voice for Kênh 1.

Voice preset: nữ trẻ miền Nam (young female, Southern Vietnam accent, warm, friendly).
Output: PCM/WAV saved to backend/static/audio/, returns relative URL.
"""
from __future__ import annotations

import asyncio
import base64
import logging
import uuid
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

_AUDIO_DIR = Path(__file__).resolve().parent.parent / "static" / "audio"
_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

try:
    from google import genai
    from google.genai import types as genai_types
except ImportError:
    genai = None  # type: ignore[assignment]
    genai_types = None  # type: ignore[assignment]


# ── Custom Exceptions ──────────────────────────────────────────────────────────


class GeminiTTSRateLimitError(Exception):
    """429 — Vượt quota Gemini TTS."""


class GeminiTTSAuthError(Exception):
    """401/403 — API key sai."""


class GeminiTTSTimeoutError(Exception):
    """Timeout khi gọi API."""


# ── Config ─────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class GeminiTTSConfig:
    """Cấu hình GeminiTTSEngine cho Kênh 1."""

    api_key: str
    model: str = "gemini-2.5-flash-preview-tts"
    voice_name: str = "Aoede"  # female, warm voice
    style_prompt: str = (
        "Giọng nữ trẻ khoảng 25-30 tuổi, miền Nam Việt Nam, "
        "ấm áp, thân thiện, tốc độ vừa phải, phù hợp review sản phẩm mẹ và bé."
    )
    timeout_seconds: float = 60.0


# ── Result DTO ─────────────────────────────────────────────────────────────────


@dataclass
class TTSResult:
    """Kết quả generate TTS từ Gemini."""

    audio_url: str   # /static/audio/<uuid>.wav
    audio_path: Path
    duration_seconds: float


# ── Engine ────────────────────────────────────────────────────────────────────


class GeminiTTSEngine:
    """Tổng hợp giọng nữ trẻ miền Nam từ Gemini TTS API.

    Pattern:
        engine = GeminiTTSEngine(config)
        result = await engine.generate("Xin chào các mẹ bầu!")
    """

    def __init__(self, config: GeminiTTSConfig) -> None:
        if genai is None:
            raise ImportError(
                "google-genai not installed. Run: pip install google-genai"
            )
        self.config = config
        self._client = genai.Client(api_key=config.api_key)

    async def generate(self, text: str) -> TTSResult:
        """Generate TTS. Raises ValueError for empty text, typed errors on API failure."""
        if not text.strip():
            raise ValueError("text must not be empty")

        full_prompt = f"[{self.config.style_prompt}]\n\n{text}"

        try:
            audio_bytes = await self._call_api(full_prompt)
        except (GeminiTTSRateLimitError, GeminiTTSAuthError, GeminiTTSTimeoutError):
            raise
        except Exception:
            logger.error("Gemini TTS failed for text: %.50s", text)
            raise

        file_id = uuid.uuid4().hex
        audio_path = _AUDIO_DIR / f"{file_id}.wav"
        audio_path.write_bytes(audio_bytes)

        # 24kHz, 16-bit PCM — estimate duration
        duration = len(audio_bytes) / (24000 * 2)
        return TTSResult(
            audio_url=f"/static/audio/{file_id}.wav",
            audio_path=audio_path,
            duration_seconds=max(duration, 0.1),
        )

    async def _call_api(self, prompt: str) -> bytes:
        """Call Gemini TTS API synchronously wrapped in asyncio thread."""
        def _sync() -> bytes:
            response = self._client.models.generate_content(
                model=self.config.model,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=genai_types.SpeechConfig(
                        voice_config=genai_types.VoiceConfig(
                            prebuilt_voice_config=genai_types.PrebuiltVoiceConfig(
                                voice_name=self.config.voice_name,
                            )
                        ),
                    ),
                ),
            )
            data = response.candidates[0].content.parts[0].inline_data.data
            return base64.b64decode(data) if isinstance(data, str) else data

        try:
            return await asyncio.wait_for(
                asyncio.to_thread(_sync), timeout=self.config.timeout_seconds
            )
        except asyncio.TimeoutError as e:
            raise GeminiTTSTimeoutError("Gemini TTS timeout") from e
