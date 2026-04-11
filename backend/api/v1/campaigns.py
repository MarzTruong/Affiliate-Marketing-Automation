from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.campaign import Campaign
from backend.models.product import Product
from backend.schemas.campaign import (
    CampaignCreate,
    CampaignResponse,
    CampaignUpdate,
    ProductCreate,
    ProductResponse,
    ProductSearchRequest,
    ProductSearchResponse,
)

router = APIRouter()


@router.post("", response_model=CampaignResponse, status_code=201)
async def create_campaign(data: CampaignCreate, db: AsyncSession = Depends(get_db)):
    campaign = Campaign(**data.model_dump())
    db.add(campaign)
    await db.flush()
    await db.refresh(campaign)
    return campaign


@router.get("", response_model=list[CampaignResponse])
async def list_campaigns(
    status: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(Campaign).offset(skip).limit(limit).order_by(Campaign.created_at.desc())
    if status:
        query = query.where(Campaign.status == status)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(campaign_id: UUID, db: AsyncSession = Depends(get_db)):
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.patch("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: UUID, data: CampaignUpdate, db: AsyncSession = Depends(get_db)
):
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(campaign, key, value)
    await db.flush()
    await db.refresh(campaign)
    return campaign


@router.post("/{campaign_id}/activate", response_model=CampaignResponse)
async def activate_campaign(campaign_id: UUID, db: AsyncSession = Depends(get_db)):
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    campaign.status = "active"
    await db.flush()
    await db.refresh(campaign)
    return campaign


@router.post("/{campaign_id}/products/search", response_model=list[ProductSearchResponse])
async def search_products_on_platform(
    campaign_id: UUID,
    data: ProductSearchRequest,
    db: AsyncSession = Depends(get_db),
):
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Import connector dynamically based on campaign platform
    from backend.connectors import get_connector

    connector = get_connector(campaign.platform)
    products = await connector.search_products(
        query=data.query, category=data.category, limit=data.limit
    )
    return products


@router.post("/{campaign_id}/products", response_model=ProductResponse, status_code=201)
async def add_campaign_product(
    campaign_id: UUID, data: ProductCreate, db: AsyncSession = Depends(get_db)
):
    """Thêm sản phẩm thủ công vào chiến dịch."""
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    product = Product(
        campaign_id=campaign_id,
        platform=campaign.platform,
        name=data.name,
        original_url=data.original_url,
        affiliate_url=data.affiliate_url,
        price=data.price,
        category=data.category,
        commission_rate=data.commission_rate,
        external_product_id=data.external_product_id,
        metadata_json={"description": data.description} if data.description else None,
    )
    db.add(product)
    await db.flush()
    await db.refresh(product)
    return product


@router.delete("/{campaign_id}/products/{product_id}", status_code=204)
async def delete_campaign_product(
    campaign_id: UUID, product_id: UUID, db: AsyncSession = Depends(get_db)
):
    """Xóa sản phẩm khỏi chiến dịch."""
    product = await db.get(Product, product_id)
    if not product or product.campaign_id != campaign_id:
        raise HTTPException(status_code=404, detail="Product not found")
    await db.delete(product)


@router.get("/{campaign_id}/products", response_model=list[ProductResponse])
async def list_campaign_products(campaign_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Product).where(Product.campaign_id == campaign_id).order_by(Product.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{campaign_id}/stats")
async def get_campaign_stats(campaign_id: UUID, db: AsyncSession = Depends(get_db)):
    from backend.models.analytics import AnalyticsEvent
    from backend.models.content import ContentPiece

    product_count = await db.scalar(
        select(func.count()).where(Product.campaign_id == campaign_id)
    )
    content_count = await db.scalar(
        select(func.count()).where(ContentPiece.campaign_id == campaign_id)
    )
    total_clicks = await db.scalar(
        select(func.count()).where(
            AnalyticsEvent.campaign_id == campaign_id,
            AnalyticsEvent.event_type == "click",
        )
    ) or 0
    total_revenue = await db.scalar(
        select(func.coalesce(func.sum(AnalyticsEvent.value), 0)).where(
            AnalyticsEvent.campaign_id == campaign_id,
            AnalyticsEvent.event_type == "revenue",
        )
    ) or 0

    return {
        "product_count": product_count,
        "content_count": content_count,
        "total_clicks": total_clicks,
        "total_revenue": float(total_revenue),
    }
