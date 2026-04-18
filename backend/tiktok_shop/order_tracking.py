"""OrderTrackingClient — pull recent affiliate orders for Loop 5 feedback."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from backend.tiktok_shop.connector import TikTokShopConnector


@dataclass(frozen=True)
class OrderResult:
    order_id: str
    product_id: str
    status: str
    commission_amount: float
    created_at: datetime


class OrderTrackingClient:
    def __init__(self, connector: TikTokShopConnector) -> None:
        self.connector = connector

    async def list_recent(self, days: int = 7) -> list[OrderResult]:
        """List orders from the last N days."""
        start = datetime.now(timezone.utc) - timedelta(days=days)
        resp = await self.connector._request(
            "GET",
            "/affiliate_creator/202309/orders/list",
            {"start_time": int(start.timestamp()), "page_size": 100},
        )
        orders = resp.get("data", {}).get("orders", [])
        return [
            OrderResult(
                order_id=o["order_id"],
                product_id=o["product_id"],
                status=o["status"],
                commission_amount=float(o.get("commission_amount", 0)),
                created_at=datetime.fromisoformat(
                    o["created_at"].replace("Z", "+00:00")
                ),
            )
            for o in orders
        ]
