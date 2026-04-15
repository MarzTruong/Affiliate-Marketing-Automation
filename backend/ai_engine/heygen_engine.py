"""HeyGenVideoGenerator — Tạo avatar video clips cho TikTok faceless review.

Chức năng chính:
  - Gọi HeyGen API v2 để tạo clip hook (0–3s) và CTA (36–45s)
  - Async polling: submit job → đợi render xong → trả về video URL
  - Tạo 2 clips song song bằng asyncio.gather
  - Error handling: rate limit, auth, timeout, render failed
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Literal

import httpx

logger = logging.getLogger(__name__)

_API_BASE = "https://api.heygen.com"
_POLL_INTERVAL_S = 10       # Poll status mỗi 10 giây
_DEFAULT_TIMEOUT_S = 600    # Tối đa 10 phút chờ render


# ── Custom Exceptions ──────────────────────────────────────────────────────────

class HeyGenRateLimitError(Exception):
    """429 — Vượt quá request limit của HeyGen."""


class HeyGenAuthError(Exception):
    """401/403 — API key sai hoặc không hợp lệ."""


class HeyGenTimeoutError(Exception):
    """Video render quá lâu — vượt quá max_wait_s."""


class HeyGenRenderError(Exception):
    """HeyGen trả về status 'failed' trong quá trình render."""


class HeyGenError(Exception):
    """Lỗi HeyGen API chung."""


# ── Config ─────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class HeyGenConfig:
    """Cấu hình kết nối HeyGen API."""

    api_key: str = ""
    avatar_id: str = ""      # ID avatar đã tạo trên HeyGen (Photo/Digital Twin)
    voice_id: str = ""       # Voice ID trên HeyGen (dùng cho lip sync)

    # Kích thước video TikTok portrait
    width: int = 1080
    height: int = 1920

    # Avatar style: "normal" | "circle" | "closeup"
    avatar_style: str = "normal"

    # Speed: 1.0 = bình thường
    speed: float = 1.0

    # HTTP timeout (giây) — chỉ cho request gửi/nhận, không phải render time
    request_timeout: float = 30.0


# ── Result DTOs ────────────────────────────────────────────────────────────────

@dataclass
class ClipJob:
    """Job đã submit lên HeyGen, đang chờ render."""
    video_id: str
    clip_type: str  # "hook" | "cta"


@dataclass
class ClipResult:
    """Kết quả render clip từ HeyGen."""
    video_id: str
    video_url: str
    clip_type: str        # "hook" | "cta"
    duration_hint_s: int  # Ước tính thời lượng (giây)


@dataclass
class HeyGenScriptParts:
    """Nội dung VOICE được tách cho từng loại clip."""
    hook_text: str = ""   # Text cho clip 0–3s
    cta_text: str = ""    # Text cho clip 36–45s


# ── Engine ────────────────────────────────────────────────────────────────────

class HeyGenVideoGenerator:
    """Tạo avatar video clips từ script TikTok bằng HeyGen API.

    Pattern:
        engine = HeyGenVideoGenerator(config)
        await engine.initialize()
        if engine.is_available():
            results = await engine.generate_clips(script_body)
    """

    def __init__(self, config: HeyGenConfig):
        self.config = config
        self._initialized = False

    async def initialize(self) -> None:
        """Validate API key và config. Gọi một lần trong app lifespan."""
        if not self.config.api_key:
            logger.info("[HeyGenEngine] Không có API key — chạy ở scaffold mode.")
            return
        if not self.config.avatar_id:
            logger.info("[HeyGenEngine] Không có Avatar ID — chạy ở scaffold mode.")
            return
        if not self.config.voice_id:
            logger.info("[HeyGenEngine] Không có Voice ID — chạy ở scaffold mode.")
            return

        try:
            # Validate key bằng cách kiểm tra remaining credits
            async with httpx.AsyncClient(timeout=self.config.request_timeout) as client:
                resp = await client.get(
                    f"{_API_BASE}/v2/user/remaining_quota",
                    headers=self._headers(),
                )
            if resp.status_code == 401:
                logger.error("[HeyGenEngine] API key không hợp lệ (401).")
                return
            if resp.status_code not in (200, 404):  # 404 = endpoint không tồn tại nhưng key ok
                logger.warning(
                    "[HeyGenEngine] Quota check trả về %d — tiếp tục với key hiện tại.",
                    resp.status_code,
                )
            self._initialized = True
            logger.info("[HeyGenEngine] Khởi tạo thành công. Avatar: %s", self.config.avatar_id)
        except httpx.TimeoutException:
            logger.warning("[HeyGenEngine] Timeout khi validate API key — bỏ qua, thử lại sau.")
        except Exception as e:
            logger.error("[HeyGenEngine] Lỗi khởi tạo: %s", e)

    def is_available(self) -> bool:
        return self._initialized

    def _headers(self) -> dict[str, str]:
        return {
            "X-Api-Key": self.config.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    # ── Submit Job ─────────────────────────────────────────────────────────────

    async def submit_clip(
        self,
        text: str,
        clip_type: Literal["hook", "cta"],
    ) -> ClipJob:
        """Submit một clip job lên HeyGen. Trả về ngay (không đợi render).

        Args:
            text: Nội dung avatar sẽ nói.
            clip_type: "hook" (intro) hoặc "cta" (outro).

        Returns:
            ClipJob với video_id để poll sau.

        Raises:
            HeyGenAuthError, HeyGenRateLimitError, HeyGenError
        """
        text = text.strip()
        if not text:
            raise ValueError(f"[HeyGenEngine] Text clip '{clip_type}' không được rỗng.")
        if len(text) > 5000:
            text = text[:5000]
            logger.warning("[HeyGenEngine] Text clip '%s' bị cắt xuống 5000 chars.", clip_type)

        payload = {
            "video_inputs": [
                {
                    "character": {
                        "type": "avatar",
                        "avatar_id": self.config.avatar_id,
                        "avatar_style": self.config.avatar_style,
                    },
                    "voice": {
                        "type": "text",
                        "input_text": text,
                        "voice_id": self.config.voice_id,
                        "speed": self.config.speed,
                    },
                }
            ],
            "dimension": {
                "width": self.config.width,
                "height": self.config.height,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=self.config.request_timeout) as client:
                resp = await client.post(
                    f"{_API_BASE}/v2/video/generate",
                    headers=self._headers(),
                    json=payload,
                )

            self._raise_for_status(resp, context=f"submit_clip/{clip_type}")
            data = resp.json().get("data", {})
            video_id = data.get("video_id") or resp.json().get("video_id")

            if not video_id:
                raise HeyGenError(
                    f"HeyGen không trả về video_id. Response: {resp.text[:200]}"
                )

            logger.info(
                "[HeyGenEngine] Submitted clip '%s' — video_id=%s", clip_type, video_id
            )
            return ClipJob(video_id=video_id, clip_type=clip_type)

        except (HeyGenAuthError, HeyGenRateLimitError, HeyGenError):
            raise
        except httpx.TimeoutException as e:
            raise HeyGenTimeoutError(f"Timeout khi submit clip '{clip_type}': {e}") from e
        except Exception as e:
            raise HeyGenError(f"Lỗi khi submit clip '{clip_type}': {e}") from e

    # ── Poll Status ────────────────────────────────────────────────────────────

    async def wait_for_render(
        self,
        job: ClipJob,
        max_wait_s: int = _DEFAULT_TIMEOUT_S,
    ) -> ClipResult:
        """Poll HeyGen cho đến khi video render xong.

        Args:
            job: ClipJob từ submit_clip().
            max_wait_s: Thời gian tối đa chờ (giây). Default 600s = 10 phút.

        Returns:
            ClipResult với video_url.

        Raises:
            HeyGenTimeoutError: Quá max_wait_s mà chưa xong.
            HeyGenRenderError: HeyGen báo status 'failed'.
        """
        elapsed = 0
        logger.info(
            "[HeyGenEngine] Polling '%s' (video_id=%s, max=%ds)...",
            job.clip_type, job.video_id, max_wait_s,
        )

        while elapsed < max_wait_s:
            await asyncio.sleep(_POLL_INTERVAL_S)
            elapsed += _POLL_INTERVAL_S

            try:
                async with httpx.AsyncClient(timeout=self.config.request_timeout) as client:
                    resp = await client.get(
                        f"{_API_BASE}/v1/video/{job.video_id}",
                        headers=self._headers(),
                    )
                self._raise_for_status(resp, context=f"poll/{job.clip_type}")
                payload = resp.json().get("data", {})
                status = payload.get("status", "")

                if status == "completed":
                    video_url = payload.get("video_url", "")
                    if not video_url:
                        raise HeyGenRenderError(
                            f"Clip '{job.clip_type}' completed nhưng không có video_url."
                        )
                    logger.info(
                        "[HeyGenEngine] Clip '%s' done in %ds — %s",
                        job.clip_type, elapsed, video_url,
                    )
                    return ClipResult(
                        video_id=job.video_id,
                        video_url=video_url,
                        clip_type=job.clip_type,
                        duration_hint_s=3 if job.clip_type == "hook" else 10,
                    )

                if status == "failed":
                    error = payload.get("error") or "unknown error"
                    raise HeyGenRenderError(
                        f"CẢNH BÁO: HeyGen render thất bại — clip '{job.clip_type}' — {error}"
                    )

                logger.debug(
                    "[HeyGenEngine] Clip '%s' status=%s, elapsed=%ds",
                    job.clip_type, status, elapsed,
                )

            except (HeyGenRenderError, HeyGenAuthError):
                raise
            except Exception as e:
                logger.warning(
                    "[HeyGenEngine] Poll error (will retry): %s", e
                )

        raise HeyGenTimeoutError(
            f"Clip '{job.clip_type}' (video_id={job.video_id}) "
            f"chưa xong sau {max_wait_s}s. Kiểm tra HeyGen dashboard."
        )

    # ── Main: Generate Both Clips ──────────────────────────────────────────────

    async def generate_clips(
        self,
        script_body: str,
        max_wait_s: int = _DEFAULT_TIMEOUT_S,
    ) -> list[ClipResult]:
        """Tạo hook clip và CTA clip song song từ TikTok script.

        1. Extract hook text + CTA text từ VOICE column của bảng script
        2. Submit cả 2 jobs song song
        3. Poll song song đợi render
        4. Trả về list[ClipResult]

        Clips nào lỗi sẽ bị bỏ qua — trả về những cái thành công.
        """
        if not self.is_available():
            raise HeyGenError(
                "HeyGen engine chưa khởi tạo. Kiểm tra API key, Avatar ID, Voice ID."
            )

        parts = extract_script_parts(script_body)
        tasks_to_run: list[tuple[str, str]] = []

        if parts.hook_text:
            tasks_to_run.append((parts.hook_text, "hook"))
        else:
            logger.warning("[HeyGenEngine] Không tìm thấy hook text — bỏ qua hook clip.")

        if parts.cta_text:
            tasks_to_run.append((parts.cta_text, "cta"))
        else:
            logger.warning("[HeyGenEngine] Không tìm thấy CTA text — bỏ qua CTA clip.")

        if not tasks_to_run:
            logger.warning("[HeyGenEngine] Không có clip nào để tạo.")
            return []

        # Submit tất cả jobs song song
        submit_coros = [self.submit_clip(text, clip_type) for text, clip_type in tasks_to_run]
        submit_results = await asyncio.gather(*submit_coros, return_exceptions=True)

        jobs: list[ClipJob] = []
        for i, result in enumerate(submit_results):
            if isinstance(result, Exception):
                logger.error(
                    "[HeyGenEngine] Submit '%s' thất bại: %s",
                    tasks_to_run[i][1], result,
                )
            else:
                jobs.append(result)

        if not jobs:
            return []

        # Poll tất cả jobs song song
        poll_coros = [self.wait_for_render(job, max_wait_s) for job in jobs]
        poll_results = await asyncio.gather(*poll_coros, return_exceptions=True)

        clips: list[ClipResult] = []
        for result in poll_results:
            if isinstance(result, Exception):
                logger.error("[HeyGenEngine] Render thất bại: %s", result)
            else:
                clips.append(result)

        return clips

    # ── Error Mapping ──────────────────────────────────────────────────────────

    def _raise_for_status(self, resp: httpx.Response, context: str = "") -> None:
        """Raise exception phù hợp dựa trên HTTP status code."""
        if resp.status_code == 200:
            return
        if resp.status_code in (401, 403):
            raise HeyGenAuthError(
                f"CẢNH BÁO: HẾT QUOTA API — HeyGen — 401/403 [{context}]"
            )
        if resp.status_code == 429:
            raise HeyGenRateLimitError(
                f"CẢNH BÁO: HẾT QUOTA API — HeyGen — 429 Rate Limit [{context}]"
            )
        if resp.status_code >= 400:
            raise HeyGenError(
                f"HeyGen API lỗi {resp.status_code} [{context}]: {resp.text[:200]}"
            )


# ── Script Parts Extractor ─────────────────────────────────────────────────────

def extract_script_parts(script_body: str) -> HeyGenScriptParts:
    """Tách nội dung VOICE thành hook text và CTA text từ TikTok script table.

    Hook = dòng có timing bắt đầu bằng 0 (ví dụ: "0–3s", "0-3s")
    CTA  = dòng có timing bắt đầu bằng 36 (ví dụ: "36–45s", "36-45s")

    Trả về HeyGenScriptParts. Các field rỗng nếu không tìm thấy.
    """
    if not script_body:
        return HeyGenScriptParts()

    hook_text = ""
    cta_text = ""

    # Pattern: | time_cell | voice_cell | visual_cell |
    row_pattern = re.compile(r"^\|([^|]+)\|([^|]+)\|[^|]*\|", re.MULTILINE)

    for match in row_pattern.finditer(script_body):
        time_cell = match.group(1).strip()
        voice_cell = match.group(2).strip()

        # Bỏ qua header và separator
        if not time_cell or re.match(r"^[-:\s⏱]+$", time_cell):
            continue
        if "voice" in voice_cell.lower() or "🎙" in voice_cell:
            continue
        if re.match(r"^[-:\s]+$", voice_cell):
            continue

        # Làm sạch voice text
        cleaned = re.sub(r"[*`]", "", voice_cell).strip()
        cleaned = cleaned.strip('"\'""''')

        # Hook: timing bắt đầu bằng 0
        if re.match(r"^0[\s\-–]", time_cell) and cleaned:
            hook_text = cleaned

        # CTA: timing bắt đầu bằng 36
        if re.match(r"^3[5-9]|^4[0-5]", time_cell) and cleaned:
            cta_text = cleaned

    return HeyGenScriptParts(hook_text=hook_text, cta_text=cta_text)


# ── Factory ───────────────────────────────────────────────────────────────────

def create_heygen_engine() -> HeyGenVideoGenerator:
    """Factory — tạo HeyGenVideoGenerator từ settings hiện tại."""
    from backend.config import settings

    config = HeyGenConfig(
        api_key=settings.heygen_api_key,
        avatar_id=settings.heygen_avatar_id,
        voice_id=settings.heygen_voice_id,
    )
    return HeyGenVideoGenerator(config=config)
