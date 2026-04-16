import csv
import io
from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.analytics import AnalyticsEvent
from backend.models.content import ContentPiece
from backend.models.fraud_event import FraudEvent

router = APIRouter()


@router.get("/overview")
async def get_overview(
    start_date: date | None = None,
    end_date: date | None = None,
    campaign_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
):
    if not start_date:
        start_date = date.today() - timedelta(days=30)
    if not end_date:
        end_date = date.today()

    base_filter = [
        AnalyticsEvent.event_time >= start_date,
        AnalyticsEvent.event_time <= end_date,
    ]
    if campaign_id:
        base_filter.append(AnalyticsEvent.campaign_id == campaign_id)

    total_clicks = (
        await db.scalar(
            select(func.count()).where(*base_filter, AnalyticsEvent.event_type == "click")
        )
        or 0
    )

    total_conversions = (
        await db.scalar(
            select(func.count()).where(*base_filter, AnalyticsEvent.event_type == "conversion")
        )
        or 0
    )

    total_revenue = (
        await db.scalar(
            select(func.coalesce(func.sum(AnalyticsEvent.value), 0)).where(
                *base_filter, AnalyticsEvent.event_type == "revenue"
            )
        )
        or 0
    )

    total_impressions = (
        await db.scalar(
            select(func.count()).where(*base_filter, AnalyticsEvent.event_type == "impression")
        )
        or 0
    )

    ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
    conversion_rate = (total_conversions / total_clicks * 100) if total_clicks > 0 else 0

    return {
        "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
        "total_clicks": total_clicks,
        "total_conversions": total_conversions,
        "total_revenue": float(total_revenue),
        "total_impressions": total_impressions,
        "ctr": round(ctr, 2),
        "conversion_rate": round(conversion_rate, 2),
    }


@router.get("/daily")
async def get_daily_stats(
    start_date: date | None = None,
    end_date: date | None = None,
    campaign_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
):
    if not start_date:
        start_date = date.today() - timedelta(days=30)
    if not end_date:
        end_date = date.today()

    base_filter = [
        AnalyticsEvent.event_time >= start_date,
        AnalyticsEvent.event_time <= end_date,
    ]
    if campaign_id:
        base_filter.append(AnalyticsEvent.campaign_id == campaign_id)

    day_col = func.date(AnalyticsEvent.event_time).label("day")

    result = await db.execute(
        select(
            day_col,
            AnalyticsEvent.event_type,
            func.count().label("count"),
            func.coalesce(func.sum(AnalyticsEvent.value), 0).label("total_value"),
        )
        .where(*base_filter)
        .group_by(day_col, AnalyticsEvent.event_type)
        .order_by(day_col)
    )

    rows = result.all()
    daily = {}
    for row in rows:
        day_str = str(row.day)
        if day_str not in daily:
            daily[day_str] = {
                "date": day_str,
                "clicks": 0,
                "conversions": 0,
                "revenue": 0,
                "impressions": 0,
            }
        if row.event_type == "click":
            daily[day_str]["clicks"] = row.count
        elif row.event_type == "conversion":
            daily[day_str]["conversions"] = row.count
        elif row.event_type == "revenue":
            daily[day_str]["revenue"] = float(row.total_value)
        elif row.event_type == "impression":
            daily[day_str]["impressions"] = row.count

    return list(daily.values())


@router.get("/fraud-alerts")
async def get_fraud_alerts(
    resolved: bool | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(FraudEvent).offset(skip).limit(limit).order_by(FraudEvent.flagged_at.desc())
    if resolved is not None:
        query = query.where(FraudEvent.resolved == resolved)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/costs")
async def get_cost_summary(
    start_date: date | None = None,
    end_date: date | None = None,
    db: AsyncSession = Depends(get_db),
):

    if not start_date:
        start_date = date.today() - timedelta(days=30)
    if not end_date:
        end_date = date.today()

    result = await db.execute(
        select(
            ContentPiece.content_type,
            func.count().label("count"),
            func.coalesce(func.sum(ContentPiece.token_cost_input), 0).label("total_input_tokens"),
            func.coalesce(func.sum(ContentPiece.token_cost_output), 0).label("total_output_tokens"),
            func.coalesce(func.sum(ContentPiece.estimated_cost_usd), 0).label("total_cost"),
        )
        .where(
            ContentPiece.created_at >= start_date,
            ContentPiece.created_at <= end_date,
        )
        .group_by(ContentPiece.content_type)
    )

    rows = result.all()
    return [
        {
            "content_type": row.content_type,
            "count": row.count,
            "total_input_tokens": row.total_input_tokens,
            "total_output_tokens": row.total_output_tokens,
            "total_cost_usd": float(row.total_cost),
        }
        for row in rows
    ]


@router.get("/by-platform")
async def get_platform_breakdown(
    start_date: date | None = None,
    end_date: date | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Phân tích hiệu suất theo từng nền tảng."""
    if not start_date:
        start_date = date.today() - timedelta(days=30)
    if not end_date:
        end_date = date.today()

    base_filter = [
        AnalyticsEvent.event_time >= start_date,
        AnalyticsEvent.event_time <= end_date,
        AnalyticsEvent.platform.isnot(None),
    ]

    result = await db.execute(
        select(
            AnalyticsEvent.platform,
            AnalyticsEvent.event_type,
            func.count().label("count"),
            func.coalesce(func.sum(AnalyticsEvent.value), 0).label("total_value"),
        )
        .where(*base_filter)
        .group_by(AnalyticsEvent.platform, AnalyticsEvent.event_type)
        .order_by(AnalyticsEvent.platform)
    )

    rows = result.all()
    platforms: dict = {}
    for row in rows:
        p = row.platform
        if p not in platforms:
            platforms[p] = {
                "platform": p,
                "clicks": 0,
                "conversions": 0,
                "revenue": 0,
                "impressions": 0,
            }
        if row.event_type == "click":
            platforms[p]["clicks"] = row.count
        elif row.event_type == "conversion":
            platforms[p]["conversions"] = row.count
        elif row.event_type == "revenue":
            platforms[p]["revenue"] = float(row.total_value)
        elif row.event_type == "impression":
            platforms[p]["impressions"] = row.count

    for p in platforms.values():
        p["ctr"] = round((p["clicks"] / p["impressions"] * 100) if p["impressions"] > 0 else 0, 2)
        p["conversion_rate"] = round(
            (p["conversions"] / p["clicks"] * 100) if p["clicks"] > 0 else 0, 2
        )

    return list(platforms.values())


@router.get("/compare-campaigns")
async def compare_campaigns(
    campaign_ids: str = Query(..., description="Comma-separated campaign UUIDs"),
    start_date: date | None = None,
    end_date: date | None = None,
    db: AsyncSession = Depends(get_db),
):
    """So sánh hiệu suất giữa các chiến dịch."""
    if not start_date:
        start_date = date.today() - timedelta(days=30)
    if not end_date:
        end_date = date.today()

    ids = [UUID(cid.strip()) for cid in campaign_ids.split(",") if cid.strip()]

    base_filter = [
        AnalyticsEvent.event_time >= start_date,
        AnalyticsEvent.event_time <= end_date,
        AnalyticsEvent.campaign_id.in_(ids),
    ]

    result = await db.execute(
        select(
            AnalyticsEvent.campaign_id,
            AnalyticsEvent.event_type,
            func.count().label("count"),
            func.coalesce(func.sum(AnalyticsEvent.value), 0).label("total_value"),
        )
        .where(*base_filter)
        .group_by(AnalyticsEvent.campaign_id, AnalyticsEvent.event_type)
    )

    rows = result.all()
    campaigns: dict = {}
    for row in rows:
        cid = str(row.campaign_id)
        if cid not in campaigns:
            campaigns[cid] = {
                "campaign_id": cid,
                "clicks": 0,
                "conversions": 0,
                "revenue": 0,
                "impressions": 0,
            }
        if row.event_type == "click":
            campaigns[cid]["clicks"] = row.count
        elif row.event_type == "conversion":
            campaigns[cid]["conversions"] = row.count
        elif row.event_type == "revenue":
            campaigns[cid]["revenue"] = float(row.total_value)
        elif row.event_type == "impression":
            campaigns[cid]["impressions"] = row.count

    for c in campaigns.values():
        c["ctr"] = round((c["clicks"] / c["impressions"] * 100) if c["impressions"] > 0 else 0, 2)
        c["conversion_rate"] = round(
            (c["conversions"] / c["clicks"] * 100) if c["clicks"] > 0 else 0, 2
        )

    return list(campaigns.values())


@router.get("/export")
async def export_analytics_csv(
    start_date: date | None = None,
    end_date: date | None = None,
    campaign_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Xuất dữ liệu phân tích ra file CSV."""
    if not start_date:
        start_date = date.today() - timedelta(days=30)
    if not end_date:
        end_date = date.today()

    base_filter = [
        AnalyticsEvent.event_time >= start_date,
        AnalyticsEvent.event_time <= end_date,
    ]
    if campaign_id:
        base_filter.append(AnalyticsEvent.campaign_id == campaign_id)

    result = await db.execute(
        select(AnalyticsEvent).where(*base_filter).order_by(AnalyticsEvent.event_time)
    )
    events = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Thời gian", "Loại sự kiện", "Nền tảng", "Chiến dịch", "Sản phẩm", "Giá trị"])

    for e in events:
        writer.writerow(
            [
                e.event_time.isoformat() if e.event_time else "",
                e.event_type,
                e.platform or "",
                str(e.campaign_id) if e.campaign_id else "",
                str(e.product_id) if e.product_id else "",
                float(e.value) if e.value else 0,
            ]
        )

    output.seek(0)
    filename = f"analytics_{start_date}_{end_date}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
