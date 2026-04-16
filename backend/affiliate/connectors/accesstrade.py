"""AccessTrade Vietnam connector với Rate Limiter và Exponential Backoff.

Thay thế Shopee unofficial scraping API.
AccessTrade là nguồn quét sản phẩm chính — hỗ trợ Shopee, Lazada, Tiki qua 1 API.
"""

import asyncio
import logging
from datetime import date

import httpx
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from backend.affiliate.connectors.base import AffiliateLink, BasePlatformConnector, ProductInfo
from backend.config import settings

logger = logging.getLogger(__name__)


# ── Custom Exceptions ────────────────────────────────────────────────────────


class RateLimitError(Exception):
    """HTTP 429 — bị rate limit, cần backoff."""


class AuthError(Exception):
    """HTTP 401/403 — sai credentials, không nên retry."""


class ConnectorNetworkError(Exception):
    """Network timeout / connection error — có thể retry."""


# ── Rate Limiter ─────────────────────────────────────────────────────────────


class RateLimiter:
    """Token bucket đơn giản — giới hạn số request mỗi giây."""

    def __init__(self, delay_seconds: float = 0.5):
        self._delay = delay_seconds
        self._last_call: float = 0.0

    async def acquire(self) -> None:
        now = asyncio.get_event_loop().time()
        wait = self._delay - (now - self._last_call)
        if wait > 0:
            await asyncio.sleep(wait)
        self._last_call = asyncio.get_event_loop().time()


# ── Retry decorator cho API calls ────────────────────────────────────────────


def _accesstrade_retry():
    """3 lần retry, backoff 2s → 4s → 8s, chỉ retry khi RateLimit hoặc NetworkError."""
    return retry(
        retry=retry_if_exception_type((RateLimitError, ConnectorNetworkError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        reraise=True,
    )


# ── AccessTrade Connector ─────────────────────────────────────────────────────


class AccessTradeConnector(BasePlatformConnector):
    """AccessTrade Vietnam affiliate aggregator connector.

    Một API duy nhất để tạo affiliate link và track conversion
    cho Shopee, Lazada, Tiki và các merchant khác tại VN.
    """

    BASE_URL = "https://api.accesstrade.vn/v1"
    # 0.5s delay giữa các request — tránh rate limit
    _rate_limiter = RateLimiter(delay_seconds=0.5)

    def __init__(self):
        self.api_key = settings.accesstrade_api_key
        self.site_id = settings.accesstrade_site_id
        # Reuse client — không tạo mới mỗi lần
        self.client = httpx.AsyncClient(timeout=30.0)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json",
        }

    async def _get(self, path: str, params: dict | None = None) -> dict:
        """HTTP GET với rate limit + phân loại exception rõ ràng."""
        await self._rate_limiter.acquire()
        try:
            resp = await self.client.get(
                f"{self.BASE_URL}{path}",
                params=params,
                headers=self._headers(),
            )
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            raise ConnectorNetworkError(f"Network error: {e}") from e

        if resp.status_code == 429:
            raise RateLimitError(f"Rate limited by AccessTrade (429): {path}")
        if resp.status_code in (401, 403):
            raise AuthError(f"AccessTrade auth failed ({resp.status_code}): {path}")
        if resp.status_code >= 500:
            raise ConnectorNetworkError(f"AccessTrade server error ({resp.status_code}): {path}")

        return resp.json()

    # ── Public API ────────────────────────────────────────────────────────────

    @_accesstrade_retry()
    async def _authenticate_request(self) -> bool:
        await self._get("/transactions")
        return True  # _get raises nếu auth fail

    async def authenticate(self) -> bool:
        if not self.api_key:
            return False
        try:
            return await self._authenticate_request()
        except AuthError:
            logger.warning("[AccessTrade] Credentials không hợp lệ.")
            return False
        except (RateLimitError, ConnectorNetworkError, RetryError) as e:
            logger.warning(f"[AccessTrade] Không thể xác thực: {e}")
            return False

    @_accesstrade_retry()
    async def _search_request(self, params: dict) -> list[dict]:
        data = await self._get("/offers_informations", params=params)
        return data.get("data", [])

    async def search_products(
        self, query: str, category: str | None = None, limit: int = 20
    ) -> list[ProductInfo]:
        params: dict = {"keyword": query, "limit": limit}
        if category:
            params["category"] = category

        try:
            offers = await self._search_request(params)
        except AuthError as e:
            logger.error(f"[AccessTrade] Auth error khi search: {e}")
            return []
        except (RateLimitError, ConnectorNetworkError, RetryError) as e:
            logger.warning(f"[AccessTrade] Search thất bại sau retry: {e}")
            return []

        products = []
        for offer in offers[:limit]:
            # AccessTrade trả về deals/coupons — aff_link đã là link affiliate
            aff_link = offer.get("aff_link", "")
            original_link = offer.get("link", "") or aff_link
            coupons = offer.get("coupons", [])
            coupon_text = " | ".join(
                f"{c.get('coupon_code', '')} ({c.get('coupon_desc', '')})"
                for c in coupons
                if c.get("coupon_code")
            )
            description = offer.get("content", "")
            if coupon_text:
                description = f"{description}\nMã giảm giá: {coupon_text}".strip()

            product = ProductInfo(
                external_id=str(offer.get("id", "")),
                name=offer.get("name", ""),
                price=0.0,  # deals/coupons không có giá cố định
                original_url=original_link,
                affiliate_url=aff_link,
                image_urls=[offer.get("image", "")] if offer.get("image") else [],
                description=description,
                category=offer.get("domain", ""),
                commission_rate=0.0,  # AccessTrade không expose commission trong search
                metadata={
                    "merchant": offer.get("merchant", ""),
                    "domain": offer.get("domain", ""),
                    "aff_link": aff_link,
                    "coupons": coupons,
                    "start_time": offer.get("start_time", ""),
                    "end_time": offer.get("end_time", ""),
                },
            )
            products.append(product)

        return products

    @_accesstrade_retry()
    async def _generate_link_request(self, product_url: str) -> dict:
        return await self._get(
            "/offers_informations/generate_link",
            params={"url": product_url},
        )

    async def generate_affiliate_link(self, product_url: str) -> AffiliateLink:
        # Nếu URL đã là aff_link (go.isclix.com) thì dùng luôn, không gọi thêm API
        if "go.isclix.com" in product_url or "accesstrade" in product_url:
            return AffiliateLink(original_url=product_url, affiliate_url=product_url)
        try:
            data = await self._generate_link_request(product_url)
            return AffiliateLink(
                original_url=product_url,
                affiliate_url=data.get("data", {}).get("url", product_url),
                short_url=data.get("data", {}).get("short_url"),
            )
        except (AuthError, RateLimitError, ConnectorNetworkError, RetryError) as e:
            logger.warning(f"[AccessTrade] Không tạo được affiliate link: {e}")
            return AffiliateLink(original_url=product_url, affiliate_url=product_url)

    @_accesstrade_retry()
    async def _transactions_request(self, params: dict) -> list[dict]:
        data = await self._get("/transactions", params=params)
        return data.get("data", [])

    async def get_performance_data(self, start_date: date, end_date: date) -> list[dict]:
        try:
            return await self._transactions_request(
                {
                    "since": start_date.isoformat(),
                    "until": end_date.isoformat(),
                }
            )
        except (AuthError, RateLimitError, ConnectorNetworkError, RetryError) as e:
            logger.warning(f"[AccessTrade] Không lấy được performance data: {e}")
            return []

    async def get_merchants(self) -> list[dict]:
        """Danh sách merchant trên AccessTrade VN."""
        try:
            data = await self._get("/offers_informations/merchant_list")
            return data.get("data", [])
        except (AuthError, RateLimitError, ConnectorNetworkError, RetryError) as e:
            logger.warning(f"[AccessTrade] Không lấy được danh sách merchant: {e}")
            return []
