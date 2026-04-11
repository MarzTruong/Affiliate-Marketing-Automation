from backend.connectors.base import BasePlatformConnector
from backend.connectors.shopee import ShopeeConnector
from backend.connectors.tiktok_shop import TikTokShopConnector
from backend.connectors.shopback import ShopBackConnector
from backend.connectors.accesstrade import AccessTradeConnector


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
