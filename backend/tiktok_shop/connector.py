"""TikTokShopConnector — HMAC-SHA256 signed request client for TikTok Shop Affiliate API.

Ref: https://partner.tiktokshop.com/docv2/page/affiliate-creator-api-overview
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)


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

    def _sign(self, params: dict[str, Any]) -> str:
        """HMAC-SHA256 per TikTok Shop API spec.

        Signing string: app_secret + sorted_key_value_pairs + app_secret
        """
        sorted_keys = sorted(params.keys())
        base = "".join(f"{k}{params[k]}" for k in sorted_keys)
        signing_str = f"{self.config.app_secret}{base}{self.config.app_secret}"
        return hmac.new(
            self.config.app_secret.encode(),
            signing_str.encode(),
            hashlib.sha256,
        ).hexdigest()

    async def _request(
        self, method: str, path: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Send signed request. Raises typed exceptions on HTTP errors."""
        common: dict[str, Any] = {
            "app_key": self.config.app_key,
            "access_token": self.config.access_token,
            "timestamp": int(time.time()),
            **params,
        }
        common["sign"] = self._sign(common)

        url = f"{self.config.base_url}{path}"
        async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
            try:
                resp = await client.request(method, url, params=common)
            except httpx.TimeoutException as e:
                raise TikTokShopAPIError("Request timed out") from e

        if resp.status_code in (401, 403):
            raise TikTokShopAuthError(f"HTTP {resp.status_code}: {resp.text[:200]}")
        if resp.status_code == 429:
            raise TikTokShopRateLimitError(resp.text[:200])
        if resp.status_code >= 400:
            raise TikTokShopAPIError(f"HTTP {resp.status_code}: {resp.text[:200]}")

        return resp.json()
