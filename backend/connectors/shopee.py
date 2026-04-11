"""Shopee Connector — dùng AccessTrade API làm proxy tìm kiếm và tạo link.

Shopee không có public product search API cho affiliate.
Logic cào dữ liệu unofficial (shopee.vn/api/v4) đã bị xóa —
gây ban IP và vi phạm ToS.

Thay thế: AccessTrade Vietnam hỗ trợ Shopee merchant,
cho phép search và tạo affiliate link qua 1 API chính thức.
"""

import hashlib
import hmac
import logging
import time
from datetime import date

from backend.config import settings
from backend.connectors.base import AffiliateLink, BasePlatformConnector, ProductInfo

logger = logging.getLogger(__name__)


class ShopeeConnector(BasePlatformConnector):
    """Shopee affiliate connector — search và link generation qua AccessTrade API.

    Shopee Open API (partner.shopeemobile.com) chỉ dùng cho xác thực shop.
    Toàn bộ product search và affiliate link đi qua AccessTrade.
    """

    PARTNER_BASE = "https://partner.shopeemobile.com"

    def __init__(self):
        self.partner_id = int(settings.shopee_partner_id) if settings.shopee_partner_id else 0
        self.partner_key = settings.shopee_partner_key
        self.access_token = settings.shopee_access_token
        self.shop_id = int(settings.shopee_shop_id) if settings.shopee_shop_id else 0

        # Lazy import để tránh circular dependency
        self._accesstrade: "AccessTradeConnector | None" = None

    def _get_accesstrade(self):
        if self._accesstrade is None:
            from backend.connectors.accesstrade import AccessTradeConnector
            self._accesstrade = AccessTradeConnector()
        return self._accesstrade

    # ── Shopee Partner API — chỉ dùng để xác thực shop ──────────────────────

    def _sign(self, path: str, timestamp: int) -> str:
        base_string = f"{self.partner_id}{path}{timestamp}{self.access_token}{self.shop_id}"
        return hmac.new(
            self.partner_key.encode(), base_string.encode(), hashlib.sha256
        ).hexdigest()

    async def authenticate(self) -> bool:
        """Xác thực Shopee Partner API credentials."""
        if not self.partner_key or not self.access_token:
            # Fallback: kiểm tra qua AccessTrade nếu không có Shopee credentials
            return await self._get_accesstrade().authenticate()

        import httpx
        path = "/api/v2/shop/get_shop_info"
        timestamp = int(time.time())
        params = {
            "partner_id": self.partner_id,
            "timestamp": timestamp,
            "access_token": self.access_token,
            "shop_id": self.shop_id,
            "sign": self._sign(path, timestamp),
        }
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(f"{self.PARTNER_BASE}{path}", params=params)
                data = resp.json()
                return data.get("error") == "" or data.get("error") is None
        except Exception as e:
            logger.warning(f"[Shopee] Xác thực thất bại: {e}")
            return False

    # ── Product Search — qua AccessTrade (chính thức) ────────────────────────

    async def search_products(
        self, query: str, category: str | None = None, limit: int = 20
    ) -> list[ProductInfo]:
        """Tìm sản phẩm Shopee qua AccessTrade API.

        AccessTrade có merchant Shopee VN — kết quả là các offer chính thức
        với commission rate được đảm bảo, không bị ban IP.
        """
        at = self._get_accesstrade()
        products = await at.search_products(query=query, category=category, limit=limit)

        # Tag platform = shopee cho các sản phẩm trả về
        for p in products:
            if not p.platform:
                p.platform = "shopee"

        return products

    # ── Affiliate Link — qua AccessTrade ─────────────────────────────────────

    async def generate_affiliate_link(self, product_url: str) -> AffiliateLink:
        """Tạo affiliate link Shopee qua AccessTrade."""
        return await self._get_accesstrade().generate_affiliate_link(product_url)

    async def get_performance_data(self, start_date: date, end_date: date) -> list[dict]:
        """Lấy dữ liệu conversion từ AccessTrade cho các merchant Shopee."""
        return await self._get_accesstrade().get_performance_data(start_date, end_date)
