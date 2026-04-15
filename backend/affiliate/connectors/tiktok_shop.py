import calendar
import hashlib
import hmac
import time
from datetime import date, datetime

import httpx

from backend.config import settings
from backend.affiliate.connectors.base import AffiliateLink, BasePlatformConnector, ProductInfo


class TikTokShopConnector(BasePlatformConnector):
    """TikTok Shop Affiliate Seller API connector."""

    BASE_URL = "https://open-api.tiktokglobalshop.com"

    def __init__(self):
        self.app_key = settings.tiktok_app_key
        self.app_secret = settings.tiktok_app_secret
        self.access_token = settings.tiktok_access_token
        self.client = httpx.AsyncClient(timeout=30.0)

    def _sign(self, path: str, params: dict, timestamp: int) -> str:
        """Generate HMAC-SHA256 signature for TikTok Shop API."""
        sorted_params = sorted(params.items())
        param_str = "".join(f"{k}{v}" for k, v in sorted_params)
        base_string = f"{self.app_secret}{path}{param_str}{self.app_secret}"
        return hmac.new(
            self.app_secret.encode(), base_string.encode(), hashlib.sha256
        ).hexdigest()

    async def _request(self, path: str, params: dict | None = None) -> dict:
        timestamp = int(time.time())
        all_params = {
            "app_key": self.app_key,
            "timestamp": str(timestamp),
            "access_token": self.access_token,
        }
        if params:
            all_params.update(params)

        all_params["sign"] = self._sign(path, all_params, timestamp)

        resp = await self.client.get(f"{self.BASE_URL}{path}", params=all_params)
        return resp.json()

    async def authenticate(self) -> bool:
        try:
            data = await self._request("/api/shop/get_authorized_shop")
            return data.get("code") == 0
        except Exception:
            return False

    async def search_products(
        self, query: str, category: str | None = None, limit: int = 20
    ) -> list[ProductInfo]:
        params = {
            "search_keyword": query,
            "page_size": str(limit),
            "page_number": "1",
        }

        try:
            data = await self._request("/api/products/search", params)
            items = data.get("data", {}).get("products", [])

            products = []
            for item in items[:limit]:
                skus = item.get("skus", [{}])
                first_sku = skus[0] if skus else {}
                images = [img.get("url", "") for img in item.get("images", [])]

                product = ProductInfo(
                    external_id=str(item.get("id", "")),
                    name=item.get("name", ""),
                    price=float(first_sku.get("price", {}).get("sale_price", 0)),
                    original_url=f"https://shop.tiktok.com/view/product/{item.get('id', '')}",
                    image_urls=images,
                    description=item.get("description", ""),
                    category=str(item.get("category_list", [{}])[0].get("id", "") if item.get("category_list") else ""),
                    commission_rate=float(item.get("affiliate_commission_rate", 0)),
                )
                products.append(product)

            return products
        except Exception:
            return []

    async def generate_affiliate_link(self, product_url: str) -> AffiliateLink:
        # TikTok Shop affiliate link generation via API
        try:
            data = await self._request(
                "/api/affiliate/seller/open_collaboration/product/generate_link",
                {"product_link": product_url},
            )
            affiliate_url = data.get("data", {}).get("affiliate_link", product_url)
            return AffiliateLink(
                original_url=product_url,
                affiliate_url=affiliate_url,
            )
        except Exception:
            return AffiliateLink(original_url=product_url, affiliate_url=product_url)

    async def get_performance_data(self, start_date: date, end_date: date) -> list[dict]:
        try:
            data = await self._request(
                "/api/affiliate/seller/commission/detail",
                {
                    "start_time": str(calendar.timegm(start_date.timetuple())),
                    "end_time": str(calendar.timegm(end_date.timetuple())),
                    "page_size": "100",
                    "page_number": "1",
                },
            )
            return data.get("data", {}).get("commission_details", [])
        except Exception:
            return []
