from backend.affiliate.connectors.base import BasePlatformConnector
from backend.affiliate.connectors.shopee import ShopeeConnector
from backend.affiliate.connectors.tiktok_shop import TikTokShopConnector
from backend.affiliate.connectors.shopback import ShopBackConnector
from backend.affiliate.connectors.accesstrade import AccessTradeConnector


def get_connector(platform: str) -> BasePlatformConnector:
    connectors = {
        "shopee": ShopeeConnector,
        "tiktok_shop": TikTokShopConnector,
        "shopback": ShopBackConnector,
        "accesstrade": AccessTradeConnector,
    }
    connector_class = connectors.get(platform)
    if not connector_class:
        raise ValueError(f"Unsupported platform: {platform}. Available: {list(connectors.keys())}")
    return connector_class()
