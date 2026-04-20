"""ElevenLabsAudioGenerator — Text-to-Speech với giọng clone của owner.

Chức năng chính:
  - Tổng hợp giọng đọc tiếng Việt từ script TikTok (cột VOICE)
  - Async wrapping của ElevenLabs SDK (sync → run_in_executor)
  - Lưu file MP3 vào backend/static/audio/, trả về URL relative
  - Error handling chi tiết: rate limit, auth, timeout, network
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# Thư mục lưu audio — tạo tự động nếu chưa có
_AUDIO_DIR = Path(__file__).resolve().parent.parent / "static" / "audio"

# Module-level import để test có thể patch được
try:
    from elevenlabs import VoiceSettings
    from elevenlabs.client import AsyncElevenLabs as _AsyncElevenLabs
except ImportError:
    VoiceSettings = None  # type: ignore[assignment,misc]
    _AsyncElevenLabs = None  # type: ignore[assignment,misc]


# ── Custom Exceptions ──────────────────────────────────────────────────────────


class ElevenLabsRateLimitError(Exception):
    """429 — Vượt quá quota ElevenLabs (character limit hoặc request limit)."""


class ElevenLabsAuthError(Exception):
    """401/403 — API key sai hoặc không có quyền dùng voice này."""


class ElevenLabsTimeoutError(Exception):
    """Request mất quá lâu — ElevenLabs server không phản hồi."""


class ElevenLabsError(Exception):
    """Lỗi ElevenLabs API chung."""


# ── Config ─────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ElevenLabsConfig:
    """Cấu hình kết nối ElevenLabs TTS."""

    api_key: str = ""
    voice_id: str = ""  # Voice ID sau khi clone giọng trên ElevenLabs

    # Model — eleven_multilingual_v2 hỗ trợ tiếng Việt tốt nhất
    model_id: str = "eleven_multilingual_v2"

    # Voice settings
    stability: float = 0.5  # 0.0–1.0: thấp = đa dạng, cao = ổn định
    similarity_boost: float = 0.75  # 0.0–1.0: giống giọng gốc
    style: float = 0.0  # 0.0–1.0: phong cách đọc (0 = trung tính)
    use_speaker_boost: bool = True  # Tăng độ rõ ràng

    # Output
    output_format: str = "mp3_44100_128"  # MP3 44.1kHz 128kbps — chất lượng tốt cho TikTok

    # Timeout (giây)
    timeout: float = 60.0


# ── Engine ────────────────────────────────────────────────────────────────────


class ElevenLabsAudioGenerator:
    """Tổng hợp giọng đọc từ text bằng ElevenLabs API.

    Pattern:
        engine = ElevenLabsAudioGenerator(config)
        await engine.initialize()
        if engine.is_available():
            result = await engine.generate_audio("Xin chào, đây là bài review...")
    """

    def __init__(self, config: ElevenLabsConfig):
        self.config = config
        self._client = None
        self._initialized = False

    async def initialize(self) -> None:
        """Khởi tạo ElevenLabs client. Gọi một lần trong app lifespan."""
        if not self.config.api_key:
            logger.info("[ElevenLabsEngine] Không có API key — chạy ở scaffold mode.")
            return
        if not self.config.voice_id:
            logger.info("[ElevenLabsEngine] Không có Voice ID — chạy ở scaffold mode.")
            return

        try:
            if _AsyncElevenLabs is None:
                logger.error(
                    "[ElevenLabsEngine] Thư viện elevenlabs chưa được cài đặt. "
                    "Chạy: pip install elevenlabs>=1.0.0"
                )
                return
            self._client = _AsyncElevenLabs(api_key=self.config.api_key)
            # Tạo thư mục lưu audio nếu chưa có
            _AUDIO_DIR.mkdir(parents=True, exist_ok=True)
            self._initialized = True
            logger.info("[ElevenLabsEngine] Khởi tạo thành công. Audio dir: %s", _AUDIO_DIR)
        except Exception as e:
            logger.error("[ElevenLabsEngine] Lỗi khởi tạo: %s", e)

    def is_available(self) -> bool:
        """Kiểm tra engine đã sẵn sàng dùng chưa."""
        return self._initialized and self._client is not None

    async def generate_audio(
        self,
        text: str,
        filename_prefix: str = "narration",
    ) -> AudioResult:
        """Tổng hợp giọng đọc từ text, lưu MP3, trả về AudioResult.

        Args:
            text: Văn bản cần đọc (đã extract từ cột VOICE của TikTok script).
            filename_prefix: Tiền tố tên file (ví dụ: "tiktok_review").

        Returns:
            AudioResult với file_path và audio_url.

        Raises:
            ElevenLabsRateLimitError: Hết quota.
            ElevenLabsAuthError: API key/Voice ID không hợp lệ.
            ElevenLabsTimeoutError: Request timeout.
            ElevenLabsError: Lỗi khác.
        """
        if not self.is_available():
            raise ElevenLabsError("ElevenLabs engine chưa khởi tạo. Kiểm tra API key và Voice ID.")

        text = text.strip()
        if not text:
            raise ValueError("Text không được để trống.")

        # Giới hạn ElevenLabs free tier: ~10,000 chars/tháng
        if len(text) > 5000:
            logger.warning(
                "[ElevenLabsEngine] Text dài %d chars — cắt bớt xuống 5000 để tiết kiệm quota.",
                len(text),
            )
            text = text[:5000]

        try:
            voice_settings = VoiceSettings(
                stability=self.config.stability,
                similarity_boost=self.config.similarity_boost,
                style=self.config.style,
                use_speaker_boost=self.config.use_speaker_boost,
            )

            logger.info(
                "[ElevenLabsEngine] Generating audio — voice=%s, model=%s, chars=%d",
                self.config.voice_id,
                self.config.model_id,
                len(text),
            )

            # ElevenLabs SDK v1+ trả về async generator trực tiếp — không await
            audio_bytes = b""
            async for chunk in self._client.text_to_speech.convert(
                voice_id=self.config.voice_id,
                text=text,
                model_id=self.config.model_id,
                voice_settings=voice_settings,
                output_format=self.config.output_format,
            ):
                audio_bytes += chunk

            if not audio_bytes:
                raise ElevenLabsError("ElevenLabs trả về audio rỗng.")

            # Lưu file MP3
            file_name = f"{filename_prefix}_{uuid.uuid4().hex[:8]}.mp3"
            file_path = _AUDIO_DIR / file_name
            file_path.write_bytes(audio_bytes)

            audio_url = f"/static/audio/{file_name}"
            duration_s = self._estimate_duration(text)

            logger.info(
                "[ElevenLabsEngine] Audio saved — file=%s, size=%d bytes, est=%.1fs",
                file_name,
                len(audio_bytes),
                duration_s,
            )

            return AudioResult(
                file_path=str(file_path),
                audio_url=audio_url,
                voice_id=self.config.voice_id,
                duration_s=duration_s,
                char_count=len(text),
            )

        except Exception as e:
            raise self._map_api_error(e) from e

    def _map_api_error(self, exc: Exception) -> Exception:
        """Chuyển lỗi SDK sang internal exception."""
        msg = str(exc).lower()
        if "401" in msg or "403" in msg or "unauthorized" in msg or "forbidden" in msg:
            return ElevenLabsAuthError(f"CẢNH BÁO: API key hoặc Voice ID không hợp lệ — {exc}")
        if "429" in msg or "rate limit" in msg or "quota" in msg:
            return ElevenLabsRateLimitError(f"CẢNH BÁO: HẾT QUOTA API — ElevenLabs — {exc}")
        if "timeout" in msg or "timed out" in msg:
            return ElevenLabsTimeoutError(f"ElevenLabs request timeout — {exc}")
        return ElevenLabsError(f"ElevenLabs lỗi không xác định — {exc}")

    @staticmethod
    def _estimate_duration(text: str) -> float:
        """Ước tính thời lượng audio (giây) dựa trên số từ.

        Tốc độ đọc trung bình tiếng Việt: ~120 từ/phút.
        """
        word_count = len(text.split())
        return round(word_count / 120 * 60, 1)


# ── Result DTO ─────────────────────────────────────────────────────────────────


@dataclass
class AudioResult:
    """Kết quả generate audio từ ElevenLabs."""

    file_path: str  # Đường dẫn tuyệt đối tới file MP3 trên server
    audio_url: str  # URL tương đối để truy cập qua HTTP (/static/audio/...)
    voice_id: str  # Voice ID đã dùng
    duration_s: float  # Thời lượng ước tính (giây)
    char_count: int  # Số ký tự đã tổng hợp


# ── Voice Text Extractor ───────────────────────────────────────────────────────


def extract_voice_text(script_body: str) -> str:
    """Trích xuất nội dung cột VOICE từ TikTok script markdown table.

    Script format (từ tiktok_faceless_affiliate skill):
        | 0–3s | *"Hook text"* | Camera shot |
        | 4–15s | *"Feature 1..."* | Close-up |
        ...

    Trả về: toàn bộ VOICE text nối nhau, loại bỏ markdown formatting.
    Trả về chuỗi rỗng nếu không parse được (không crash).
    """
    if not script_body:
        return ""

    voice_lines: list[str] = []

    # Pattern: dòng bảng có 3 cột: | time | voice | visual |
    # Cột VOICE là cột thứ 2 (index 1)
    row_pattern = re.compile(
        r"^\|[^|]+\|([^|]+)\|[^|]*\|",
        re.MULTILINE,
    )

    for match in row_pattern.finditer(script_body):
        voice_cell = match.group(1).strip()

        # Bỏ qua header row (chứa "VOICE" hoặc "🎙")
        if "voice" in voice_cell.lower() or "🎙" in voice_cell:
            continue
        # Bỏ qua separator row (---)
        if re.match(r"^[-:\s]+$", voice_cell):
            continue

        # Làm sạch: bỏ *, `, backtick, dấu nháy đơn/đôi nghiêng, italic
        cleaned = re.sub(r"[*`]", "", voice_cell)
        # Bỏ cặp dấu ngoặc như *"..."* hoặc "..."
        cleaned = re.sub(
            r'^["\u201c\u201d\u2018\u2019]|["\u201c\u201d\u2018\u2019]$', "", cleaned.strip()
        )
        cleaned = cleaned.strip()

        if cleaned:
            voice_lines.append(cleaned)

    if not voice_lines:
        # Fallback: trả về toàn bộ body nếu không parse được bảng
        logger.warning(
            "[ElevenLabsEngine] Không parse được VOICE table — dùng toàn bộ script body."
        )
        return script_body.strip()

    return " ".join(voice_lines)


# ── Factory ───────────────────────────────────────────────────────────────────


def create_elevenlabs_engine() -> ElevenLabsAudioGenerator:
    """Factory — tạo ElevenLabsAudioGenerator từ settings hiện tại."""
    from backend.config import settings

    config = ElevenLabsConfig(
        api_key=settings.elevenlabs_api_key,
        voice_id=settings.elevenlabs_voice_id,
    )
    return ElevenLabsAudioGenerator(config=config)
