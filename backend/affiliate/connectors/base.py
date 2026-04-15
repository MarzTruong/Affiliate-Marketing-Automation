from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date


@dataclass
class ProductInfo:
    external_id: str
    name: str
    price: float
    original_url: str
    image_urls: list[str] = field(default_factory=list)
    description: str = ""
    category: str = ""
    commission_rate: float | None = None
    metadata: dict = field(default_factory=dict)
    # Extended fields for automation pipeline
    platform: str = ""
    affiliate_url: str | None = None
    original_price: float | None = None
    rating: float | None = None
    sales_count: int | None = None

    @property
    def product_id(self) -> str:
        return self.external_id

    @property
    def image_url(self) -> str | None:
        return self.image_urls[0] if self.image_urls else None

    @property
    def product_url(self) -> str:
        return self.original_url


@dataclass
class AffiliateLink:
    original_url: str
    affiliate_url: str
    short_url: str | None = None


class BasePlatformConnector(ABC):
    """Abstract base for all platform connectors."""

    @abstractmethod
    async def authenticate(self) -> bool:
        """Test connection and validate credentials."""
        ...

    @abstractmethod
    async def search_products(
        self, query: str, category: str | None = None, limit: int = 20
    ) -> list[ProductInfo]:
        """Search for products on the platform."""
        ...

    @abstractmethod
    async def generate_affiliate_link(self, product_url: str) -> AffiliateLink:
        """Generate an affiliate link for a product URL."""
        ...

    @abstractmethod
    async def get_performance_data(
        self, start_date: date, end_date: date
    ) -> list[dict]:
        """Fetch click/conversion/revenue data for a date range."""
        ...
