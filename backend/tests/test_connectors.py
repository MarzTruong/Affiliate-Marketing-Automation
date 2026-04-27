"""Tests for platform connectors."""

import pytest

from backend.affiliate.connectors import get_connector
from backend.affiliate.connectors.accesstrade import AccessTradeConnector
from backend.affiliate.connectors.base import BasePlatformConnector
from backend.affiliate.connectors.shopback import ShopBackConnector
from backend.affiliate.connectors.shopee import ShopeeConnector


def test_get_connector_shopee():
    connector = get_connector("shopee")
    assert isinstance(connector, ShopeeConnector)
    assert isinstance(connector, BasePlatformConnector)


def test_get_connector_shopback():
    connector = get_connector("shopback")
    assert isinstance(connector, ShopBackConnector)


def test_get_connector_accesstrade():
    connector = get_connector("accesstrade")
    assert isinstance(connector, AccessTradeConnector)


def test_get_connector_unknown():
    with pytest.raises(ValueError, match="Unsupported platform"):
        get_connector("unknown_platform")


def test_get_connector_lazada_removed():
    """Lazada has been removed from supported platforms."""
    with pytest.raises(ValueError, match="Unsupported platform"):
        get_connector("lazada")


def test_get_connector_tiktok_shop_removed():
    """TikTokShopConnector removed (HMAC bug). Use backend/tiktok_shop/connector.py instead."""
    with pytest.raises(ValueError, match="Unsupported platform"):
        get_connector("tiktok_shop")


def test_all_connectors_have_required_methods():
    for platform in ["shopee", "shopback", "accesstrade"]:
        connector = get_connector(platform)
        assert hasattr(connector, "authenticate")
        assert hasattr(connector, "search_products")
        assert hasattr(connector, "generate_affiliate_link")
        assert hasattr(connector, "get_performance_data")
