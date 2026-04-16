# Backward-compat shim — real code now lives in backend.affiliate.connectors
from backend.affiliate.connectors import get_connector
from backend.affiliate.connectors.accesstrade import AccessTradeConnector
from backend.affiliate.connectors.base import BasePlatformConnector
from backend.affiliate.connectors.shopback import ShopBackConnector
from backend.affiliate.connectors.shopee import ShopeeConnector
from backend.affiliate.connectors.tiktok_shop import TikTokShopConnector

__all__ = [
    "get_connector",
    "BasePlatformConnector",
    "ShopeeConnector",
    "TikTokShopConnector",
    "ShopBackConnector",
    "AccessTradeConnector",
]
