"""TikTokShopConnector — HMAC-SHA256 signed request client for TikTok Shop Affiliate API.

Ref: https://partner.tiktokshop.com/docv2/page/affiliate-creator-api-overview
"""
from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx

from backend.config import settings

logger = logging.getLogger(__name__)


def get_connector() -> "TikTokShopConnector":
    """Build connector từ settings hiện tại (đã load từ DB)."""
    if not settings.tiktok_access_token:
        raise TikTokShopAuthError("Chưa có TikTok access token. Vào /auth/tiktok để kết nối.")
    return TikTokShopConnector(
        TikTokShopConfig(
            app_key=settings.tiktok_app_key,
            app_secret=settings.tiktok_app_secret,
            access_token=settings.tiktok_access_token,
        )
    )


class TikTokShopAuthError(Exception):
    """401/403 — Invalid credentials or access token."""


class TikTokShopRateLimitError(Exception):
    """429 — Rate limit exceeded."""


class TikTokShopAPIError(Exception):
    """Any other API error (4xx/5xx)."""


@dataclass(frozen=True)
class TikTokShopConfig:
    app_key: str
    app_secret: str
    access_token: str
    base_url: str = "https://open-api.tiktokglobalshop.com"
    timeout_seconds: float = 20.0


class TikTokShopConnector:
    """Low-level signed HTTP client. Used by ProductSearchClient + OrderTrackingClient."""

    def __init__(self, config: TikTokShopConfig) -> None:
        self.config = config

    def _sign(self, path: str, params: dict[str, Any]) -> str:
        """SHA256 (plain) per TikTok Shop API spec.

        Signing string: app_secret + path + sorted_key_value_pairs + app_secret
        Exclude: sign, access_token (these are NOT included in signing input)
        """
        exclude = {"sign", "access_token"}
        sorted_keys = sorted(k for k in params if k not in exclude)
        base = "".join(f"{k}{params[k]}" for k in sorted_keys)
        signing_str = f"{self.config.app_secret}{path}{base}{self.config.app_secret}"
        return hashlib.sha256(signing_str.encode()).hexdigest()

    async def _request(
        self, method: str, path: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Send signed request. Raises typed exceptions on HTTP errors."""
        common: dict[str, Any] = {
            "app_key": self.config.app_key,
            "timestamp": int(time.time()),
            **params,
        }
        common["sign"] = self._sign(path, common)

        url = f"{self.config.base_url}{path}"
        headers = {"x-tts-access-token": self.config.access_token}
        async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
            try:
                resp = await client.request(method, url, params=common, headers=headers)
            except httpx.TimeoutException as e:
                raise TikTokShopAPIError("Request timed out") from e

        if resp.status_code in (401, 403):
            raise TikTokShopAuthError(f"HTTP {resp.status_code}: {resp.text[:200]}")
        if resp.status_code == 429:
            raise TikTokShopRateLimitError(resp.text[:200])
        if resp.status_code >= 400:
            raise TikTokShopAPIError(f"HTTP {resp.status_code}: {resp.text[:200]}")

        return resp.json()
