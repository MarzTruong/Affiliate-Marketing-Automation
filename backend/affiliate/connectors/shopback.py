from datetime import date

import httpx

from backend.affiliate.connectors.base import AffiliateLink, BasePlatformConnector, ProductInfo
from backend.config import settings


class ShopBackConnector(BasePlatformConnector):
    """ShopBack Partner API connector for affiliate/cashback links."""

    BASE_URL = "https://api.shopback.com/partner/v1"

    def __init__(self):
        self.partner_id = settings.shopback_partner_id
        self.api_key = settings.shopback_api_key
        self.client = httpx.AsyncClient(timeout=30.0)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "X-Partner-ID": self.partner_id,
            "Content-Type": "application/json",
        }

    async def authenticate(self) -> bool:
        try:
            resp = await self.client.get(
                f"{self.BASE_URL}/account",
                headers=self._headers(),
            )
            return resp.status_code == 200
        except Exception:
            return False

    async def search_products(
        self, query: str, category: str | None = None, limit: int = 20
    ) -> list[ProductInfo]:
        # ShopBack is a cashback aggregator, not a marketplace
        # Search available merchants/stores instead
        try:
            resp = await self.client.get(
                f"{self.BASE_URL}/merchants",
                params={"keyword": query, "limit": limit, "country": "VN"},
                headers=self._headers(),
            )
            data = resp.json()
            merchants = data.get("data", [])

            products = []
            for merchant in merchants[:limit]:
                product = ProductInfo(
                    external_id=str(merchant.get("id", "")),
                    name=merchant.get("name", ""),
                    price=0,
                    original_url=merchant.get("url", ""),
                    image_urls=[merchant.get("logo", "")] if merchant.get("logo") else [],
                    description=merchant.get("description", ""),
                    category=merchant.get("category", ""),
                    commission_rate=float(merchant.get("cashback_rate", 0)),
                    metadata={"type": "merchant", "cashback": merchant.get("cashback_info", "")},
                )
                products.append(product)

            return products
        except Exception:
            return []

    async def generate_affiliate_link(self, product_url: str) -> AffiliateLink:
        try:
            resp = await self.client.post(
                f"{self.BASE_URL}/links/generate",
                json={"url": product_url},
                headers=self._headers(),
            )
            data = resp.json()
            return AffiliateLink(
                original_url=product_url,
                affiliate_url=data.get("data", {}).get("affiliate_url", product_url),
                short_url=data.get("data", {}).get("short_url"),
            )
        except Exception:
            return AffiliateLink(original_url=product_url, affiliate_url=product_url)

    async def get_performance_data(self, start_date: date, end_date: date) -> list[dict]:
        try:
            resp = await self.client.get(
                f"{self.BASE_URL}/conversions",
                params={
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                },
                headers=self._headers(),
            )
            data = resp.json()
            return data.get("data", [])
        except Exception:
            return []
