"""ProductSearchClient — search high-commission affiliate products on TikTok Shop."""
from __future__ import annotations

from dataclasses import dataclass

from backend.tiktok_shop.connector import TikTokShopConnector


@dataclass(frozen=True)
class ProductResult:
    product_id: str
    product_name: str
    price: float
    commission_rate: float
    category_name: str


class ProductSearchClient:
    def __init__(self, connector: TikTokShopConnector) -> None:
        self.connector = connector

    async def search(
        self,
        keyword: str,
        limit: int = 20,
        min_commission_rate: float = 0.10,
    ) -> list[ProductResult]:
        """Search products, filter by minimum commission rate."""
        resp = await self.connector._request(
            "GET",
            "/affiliate_creator/202309/products/search",
            {"keyword": keyword, "page_size": limit},
        )
        products = resp.get("data", {}).get("products", [])
        return [
            ProductResult(
                product_id=p["product_id"],
                product_name=p["product_name"],
                price=float(p.get("price", 0)),
                commission_rate=float(p.get("commission_rate", 0)),
                category_name=p.get("category_name", ""),
            )
            for p in products
            if float(p.get("commission_rate", 0)) >= min_commission_rate
        ]
