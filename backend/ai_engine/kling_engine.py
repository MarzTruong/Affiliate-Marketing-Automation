"""KlingEngine — fal.ai Kling 2.0 image-to-video for Kênh 1 faceless pipeline.

Generates 5-second vertical (9:16) video clips from product images.
Uses fal-client SDK. Each clip ~$0.33 (3 clips per video = ~$1.00).
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

try:
    import fal_client
except ImportError:
    fal_client = None  # type: ignore[assignment]


class KlingRateLimitError(Exception):
    """429 — Rate limit exceeded."""


class KlingAuthError(Exception):
    """401/403 — Invalid FAL_KEY."""


class KlingTimeoutError(Exception):
    """Job timed out (Kling jobs take 30-90s)."""


@dataclass(frozen=True)
class KlingConfig:
    api_key: str
    model: str = "fal-ai/kling-video/v2/master/image-to-video"
    duration_seconds: int = 5   # 5 or 10
    aspect_ratio: str = "9:16"  # TikTok vertical
    timeout_seconds: float = 180.0


@dataclass
class KlingResult:
    video_url: str      # CDN URL from fal.ai
    duration_seconds: int
    prompt: str
    image_url: str


class KlingEngine:
    def __init__(self, config: KlingConfig) -> None:
        if fal_client is None:
            raise ImportError("fal-client not installed. Run: pip install fal-client")
        self.config = config
        import os
        os.environ["FAL_KEY"] = config.api_key

    async def generate(self, image_url: str, prompt: str) -> KlingResult:
        """Generate video from image. Raises ValueError for invalid inputs."""
        if not prompt.strip():
            raise ValueError("prompt must not be empty")
        if not image_url.startswith(("http://", "https://")):
            raise ValueError("image_url must be an absolute HTTP/HTTPS URL")

        try:
            video_url = await self._submit_job(image_url, prompt)
        except KlingTimeoutError:
            raise
        except KlingAuthError:
            raise
        except KlingRateLimitError:
            raise
        return KlingResult(
            video_url=video_url,
            duration_seconds=self.config.duration_seconds,
            prompt=prompt,
            image_url=image_url,
        )

    async def _submit_job(self, image_url: str, prompt: str) -> str:
        def _sync() -> str:
            handler = fal_client.submit(
                self.config.model,
                arguments={
                    "image_url": image_url,
                    "prompt": prompt,
                    "duration": str(self.config.duration_seconds),
                    "aspect_ratio": self.config.aspect_ratio,
                },
            )
            result = handler.get()
            return result["video"]["url"]

        try:
            return await asyncio.wait_for(
                asyncio.to_thread(_sync), timeout=self.config.timeout_seconds
            )
        except asyncio.TimeoutError as e:
            logger.error(
                "Kling job timed out after %.1fs for image_url=%s",
                self.config.timeout_seconds,
                image_url,
            )
            raise KlingTimeoutError("Kling job timed out") from e
