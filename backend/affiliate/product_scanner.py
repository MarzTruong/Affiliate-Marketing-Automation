"""Product Scanner — quét và lọc sản phẩm qua AccessTrade API.

Flow:
1. Kết nối AccessTrade connector (primary source cho tất cả platforms)
2. Search sản phẩm theo keyword + category với rate limiter
3. Áp dụng bộ lọc: commission %, giá, rating, lượt bán
4. Trả về danh sách ProductInfo đạt tiêu chí
5. Nếu API chưa cấu hình hoặc rate limit → dùng mock data, log rõ lý do

Không còn scraping unofficial API (Shopee web).
Delay giữa các keyword search để tránh bị rate limit.
"""

import asyncio
import logging
from dataclasses import dataclass
from decimal import Decimal

from backend.affiliate.connectors.base import ProductInfo
from backend.models.automation import AutomationRule

logger = logging.getLogger(__name__)

# Delay giữa các keyword search (giây) — tránh rate limit AccessTrade
_KEYWORD_SEARCH_DELAY = 0.5


@dataclass
class FilterCriteria:
    """Tiêu chí lọc sản phẩm từ AutomationRule."""

    platform: str
    category: str | None
    keywords: list[str]
    min_commission_pct: Decimal | None
    min_price: Decimal | None
    max_price: Decimal | None
    min_rating: Decimal | None
    min_sales: int | None
    max_products: int

    @classmethod
    def from_rule(cls, rule: AutomationRule) -> "FilterCriteria":
        keywords = []
        if rule.keywords:
            keywords = [k.strip() for k in rule.keywords.split(",") if k.strip()]
        if rule.category and rule.category not in keywords:
            keywords.insert(0, rule.category)
        return cls(
            platform=rule.platform,
            category=rule.category,
            keywords=keywords or ["trending"],
            min_commission_pct=rule.min_commission_pct,
            min_price=rule.min_price,
            max_price=rule.max_price,
            min_rating=rule.min_rating,
            min_sales=rule.min_sales,
            max_products=rule.max_products_per_run,
        )


def _passes_filter(product: ProductInfo, criteria: FilterCriteria) -> bool:
    """Kiểm tra sản phẩm có đạt tiêu chí không.

    Deals/coupons từ AccessTrade có price=0 và commission_rate=0 —
    bỏ qua price/commission filter để không lọc nhầm deals hợp lệ.
    """
    is_deal = not product.price or product.price == 0.0

    if not is_deal:
        if criteria.min_price and product.price is not None:
            if product.price < float(criteria.min_price):
                return False
        if criteria.max_price and product.price is not None:
            if product.price > float(criteria.max_price):
                return False
        if criteria.min_commission_pct and product.commission_rate is not None:
            if product.commission_rate < float(criteria.min_commission_pct):
                return False

    if criteria.min_rating and product.rating is not None:
        if product.rating < float(criteria.min_rating):
            return False
    if criteria.min_sales and product.sales_count is not None:
        if product.sales_count < criteria.min_sales:
            return False
    return True


async def scan_products(rule: AutomationRule) -> tuple[list[ProductInfo], int]:
    """Quét và lọc sản phẩm theo AutomationRule.

    Dùng AccessTrade làm primary source.
    Fallback về mock data nếu: chưa cấu hình API key, auth fail, hoặc rate limit.

    Returns:
        (filtered_products, total_found)
    """
    criteria = FilterCriteria.from_rule(rule)

    # ── Kiểm tra AccessTrade credentials ─────────────────────────────────────
    from backend.affiliate.connectors.accesstrade import AccessTradeConnector, AuthError

    connector = AccessTradeConnector()

    if not connector.api_key:
        logger.info("[Scanner] AccessTrade API key chưa cấu hình. Dùng mock data.")
        return _mock_fallback(criteria, reason="no_api_key")

    try:
        is_auth = await connector.authenticate()
    except Exception as e:
        logger.warning(f"[Scanner] Không thể xác thực AccessTrade: {e}. Dùng mock data.")
        return _mock_fallback(criteria, reason="auth_error")

    if not is_auth:
        logger.warning("[Scanner] AccessTrade xác thực thất bại. Dùng mock data.")
        return _mock_fallback(criteria, reason="auth_failed")

    # ── Tìm sản phẩm — tối đa 3 keywords, delay giữa mỗi lần ────────────────
    all_products: list[ProductInfo] = []
    seen_ids: set[str] = set()

    from tenacity import RetryError

    from backend.affiliate.connectors.accesstrade import ConnectorNetworkError, RateLimitError

    for i, keyword in enumerate(criteria.keywords[:3]):
        # Delay giữa các keyword search (bỏ qua lần đầu)
        if i > 0:
            await asyncio.sleep(_KEYWORD_SEARCH_DELAY)

        try:
            products = await connector.search_products(
                query=keyword,
                category=criteria.category,
                limit=50,
            )
            for p in products:
                if p.product_id not in seen_ids:
                    seen_ids.add(p.product_id)
                    all_products.append(p)

        except AuthError:
            logger.error(f"[Scanner] Auth error khi search '{keyword}' — dừng scan.")
            break
        except (RateLimitError, RetryError) as e:
            # Rate limit sau retry — không tiếp tục các keyword còn lại
            logger.warning(
                f"[Scanner] Bị rate limit khi search '{keyword}': {e}. "
                f"Dừng scan, dùng {len(all_products)} SP đã tìm được."
            )
            break
        except (ConnectorNetworkError, Exception) as e:
            # Network error — skip keyword này, thử keyword tiếp
            logger.warning(f"[Scanner] Lỗi search '{keyword}' trên AccessTrade: {e}")
            continue

    total_found = len(all_products)

    # Nếu không tìm được gì (API trả về rỗng hoặc tất cả lỗi) → mock
    if total_found == 0:
        logger.info("[Scanner] AccessTrade trả về 0 sản phẩm. Dùng mock data.")
        return _mock_fallback(criteria, reason="empty_result")

    # ── Lọc và sắp xếp ───────────────────────────────────────────────────────
    filtered = [p for p in all_products if _passes_filter(p, criteria)]
    filtered.sort(
        key=lambda p: (p.commission_rate or 0, p.rating or 0, p.sales_count or 0),
        reverse=True,
    )

    logger.info(
        f"[AccessTrade] Tìm thấy {total_found} SP, "
        f"qua lọc {len(filtered)}, lấy {min(len(filtered), criteria.max_products)}"
    )
    return filtered[: criteria.max_products], total_found


def _mock_fallback(criteria: FilterCriteria, reason: str) -> tuple[list[ProductInfo], int]:
    """Trả về mock products kèm log lý do — để pipeline không bị block khi dev."""
    logger.info(f"[Scanner:MOCK] Lý do: {reason}. Platform: {criteria.platform}")
    mock = _get_mock_products(criteria)
    filtered = [p for p in mock if _passes_filter(p, criteria)]
    return filtered[: criteria.max_products], len(mock)


def _get_mock_products(criteria: FilterCriteria) -> list[ProductInfo]:
    """Mock data cho môi trường dev khi chưa có API key thật."""
    base_products = [
        ProductInfo(
            external_id="mock_001",
            name="Tai nghe Sony WH-1000XM5 chống ồn",
            description="Tai nghe không dây cao cấp, chống ồn ANC, pin 30 tiếng",
            price=7490000,
            original_price=8990000,
            image_urls=["https://via.placeholder.com/400x400?text=Sony+WH-1000XM5"],
            original_url=f"https://{criteria.platform}.vn/product/mock_001",
            affiliate_url=f"https://{criteria.platform}.vn/affiliate/mock_001",
            commission_rate=8.5,
            rating=4.8,
            sales_count=12500,
            category="Điện tử",
            platform=criteria.platform,
        ),
        ProductInfo(
            external_id="mock_002",
            name="Đầm maxi hoa nhí dự tiệc phong cách Hàn Quốc",
            description="Chất vải lụa mềm mại, thiết kế thanh lịch phù hợp nhiều dịp",
            price=285000,
            original_price=450000,
            image_urls=["https://via.placeholder.com/400x400?text=Dam+Maxi"],
            original_url=f"https://{criteria.platform}.vn/product/mock_002",
            affiliate_url=f"https://{criteria.platform}.vn/affiliate/mock_002",
            commission_rate=12.0,
            rating=4.6,
            sales_count=8900,
            category="Thời trang",
            platform=criteria.platform,
        ),
        ProductInfo(
            external_id="mock_003",
            name="Nồi chiên không dầu Xiaomi 5.5L",
            description="Công nghệ 360° Air Fry, tiết kiệm 85% dầu mỡ",
            price=1290000,
            original_price=1890000,
            image_urls=["https://via.placeholder.com/400x400?text=Xiaomi+AirFryer"],
            original_url=f"https://{criteria.platform}.vn/product/mock_003",
            affiliate_url=f"https://{criteria.platform}.vn/affiliate/mock_003",
            commission_rate=9.0,
            rating=4.7,
            sales_count=23400,
            category="Gia dụng",
            platform=criteria.platform,
        ),
        ProductInfo(
            external_id="mock_004",
            name="Serum Vitamin C The Ordinary 30ml",
            description="Serum làm sáng da, giảm thâm nám, chống oxy hóa",
            price=320000,
            original_price=420000,
            image_urls=["https://via.placeholder.com/400x400?text=Vitamin+C+Serum"],
            original_url=f"https://{criteria.platform}.vn/product/mock_004",
            affiliate_url=f"https://{criteria.platform}.vn/affiliate/mock_004",
            commission_rate=15.0,
            rating=4.9,
            sales_count=45200,
            category="Làm đẹp",
            platform=criteria.platform,
        ),
        ProductInfo(
            external_id="mock_005",
            name="Giày thể thao Nike Air Max 270",
            description="Đệm khí Max 270 siêu êm, thiết kế hiện đại năng động",
            price=2850000,
            original_price=3500000,
            image_urls=["https://via.placeholder.com/400x400?text=Nike+Air+Max"],
            original_url=f"https://{criteria.platform}.vn/product/mock_005",
            affiliate_url=f"https://{criteria.platform}.vn/affiliate/mock_005",
            commission_rate=7.5,
            rating=4.7,
            sales_count=6700,
            category="Giày dép",
            platform=criteria.platform,
        ),
    ]

    # Lọc theo danh mục nếu có
    if criteria.category:
        category_map = {
            "dien_tu": "Điện tử",
            "thoi_trang": "Thời trang",
            "gia_dung": "Gia dụng",
            "lam_dep": "Làm đẹp",
            "giay_dep": "Giày dép",
        }
        target = category_map.get(criteria.category.lower(), criteria.category)
        filtered = [p for p in base_products if target.lower() in (p.category or "").lower()]
        return filtered if filtered else base_products

    return base_products
