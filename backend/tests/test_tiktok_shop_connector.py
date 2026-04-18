"""Test TikTok Shop Connector — product search + order tracking."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from backend.tiktok_shop.connector import (
    TikTokShopAuthError,
    TikTokShopConfig,
    TikTokShopConnector,
    TikTokShopRateLimitError,
)
from backend.tiktok_shop.order_tracking import OrderResult, OrderTrackingClient
from backend.tiktok_shop.product_search import ProductResult, ProductSearchClient


@pytest.mark.unit
def test_connector_sign_returns_64_char_hex():
    cfg = TikTokShopConfig(app_key="ak", app_secret="secret", access_token="tok")
    conn = TikTokShopConnector(cfg)
    sig = conn._sign({"foo": "bar", "timestamp": 1234})
    assert isinstance(sig, str)
    assert len(sig) == 64


@pytest.mark.unit
def test_connector_sign_deterministic():
    cfg = TikTokShopConfig(app_key="ak", app_secret="secret", access_token="tok")
    conn = TikTokShopConnector(cfg)
    params = {"a": "1", "b": "2"}
    assert conn._sign(params) == conn._sign(params)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_product_search_returns_filtered_results():
    cfg = TikTokShopConfig(app_key="k", app_secret="s", access_token="t")
    conn = TikTokShopConnector(cfg)
    client = ProductSearchClient(conn)

    fake_response = {
        "data": {
            "products": [
                {
                    "product_id": "sp_001",
                    "product_name": "Sữa bầu Meiji",
                    "price": 450000,
                    "commission_rate": 0.15,
                    "category_name": "Mẹ và bé",
                },
                {
                    "product_id": "sp_002",
                    "product_name": "SP giá rẻ",
                    "price": 50000,
                    "commission_rate": 0.05,  # Below min_commission_rate
                    "category_name": "Khác",
                },
            ]
        }
    }
    with patch.object(conn, "_request", new=AsyncMock(return_value=fake_response)):
        results = await client.search(keyword="sữa bầu", limit=10, min_commission_rate=0.10)

    assert len(results) == 1
    assert isinstance(results[0], ProductResult)
    assert results[0].product_id == "sp_001"
    assert results[0].commission_rate == 0.15


@pytest.mark.unit
@pytest.mark.asyncio
async def test_order_tracking_parses_orders():
    cfg = TikTokShopConfig(app_key="k", app_secret="s", access_token="t")
    conn = TikTokShopConnector(cfg)
    client = OrderTrackingClient(conn)

    fake_response = {
        "data": {
            "orders": [
                {
                    "order_id": "ord_1",
                    "product_id": "sp_001",
                    "status": "completed",
                    "commission_amount": 67500,
                    "created_at": "2026-04-18T10:00:00Z",
                }
            ]
        }
    }
    with patch.object(conn, "_request", new=AsyncMock(return_value=fake_response)):
        orders = await client.list_recent(days=7)

    assert len(orders) == 1
    assert isinstance(orders[0], OrderResult)
    assert orders[0].commission_amount == 67500
    assert isinstance(orders[0].created_at, datetime)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_request_raises_auth_error_on_401():
    cfg = TikTokShopConfig(app_key="k", app_secret="s", access_token="bad")
    conn = TikTokShopConnector(cfg)
    with patch.object(
        conn, "_request", new=AsyncMock(side_effect=TikTokShopAuthError("401"))
    ):
        with pytest.raises(TikTokShopAuthError):
            await conn._request("GET", "/test", {})


@pytest.mark.unit
@pytest.mark.asyncio
async def test_request_raises_rate_limit_on_429():
    cfg = TikTokShopConfig(app_key="k", app_secret="s", access_token="t")
    conn = TikTokShopConnector(cfg)
    with patch.object(
        conn, "_request", new=AsyncMock(side_effect=TikTokShopRateLimitError("429"))
    ):
        with pytest.raises(TikTokShopRateLimitError):
            await conn._request("GET", "/test", {})
