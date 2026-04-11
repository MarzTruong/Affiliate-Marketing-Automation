from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class CampaignCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    platform: str = Field(..., pattern="^(shopee|tiktok_shop|shopback|accesstrade)$")
    platform_account_id: UUID | None = None
    budget_daily: Decimal | None = None
    target_category: str | None = None
    config: dict | None = None


class CampaignUpdate(BaseModel):
    name: str | None = None
    status: str | None = None
    budget_daily: Decimal | None = None
    target_category: str | None = None
    config: dict | None = None


class CampaignResponse(BaseModel):
    id: UUID
    name: str
    platform: str
    platform_account_id: UUID | None
    status: str
    budget_daily: Decimal | None
    target_category: str | None
    config: dict | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProductSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    category: str | None = None
    limit: int = Field(20, ge=1, le=50)


class ProductSearchResponse(BaseModel):
    external_id: str
    name: str
    price: float
    original_url: str
    image_urls: list[str] = []
    description: str = ""
    category: str = ""
    commission_rate: float | None = None


class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=500)
    original_url: str = Field(..., min_length=1)
    affiliate_url: str | None = None
    price: Decimal | None = None
    category: str | None = None
    commission_rate: Decimal | None = None
    external_product_id: str | None = None
    description: str | None = None


class ProductResponse(BaseModel):
    id: UUID
    campaign_id: UUID
    platform: str
    external_product_id: str | None
    name: str
    original_url: str
    affiliate_url: str | None
    price: Decimal | None
    category: str | None
    commission_rate: Decimal | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PlatformAccountCreate(BaseModel):
    platform: str = Field(..., pattern="^(shopee|tiktok_shop|shopback|accesstrade)$")
    account_name: str = Field(..., min_length=1, max_length=255)
    credentials: dict = Field(default_factory=dict)


class PlatformAccountResponse(BaseModel):
    id: UUID
    platform: str
    account_name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
