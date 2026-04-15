"""System health, monitoring, and manual task trigger endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import get_db
from backend.models.analytics import AnalyticsEvent
from backend.models.campaign import Campaign
from backend.models.content import ContentPiece
from backend.models.fraud_event import FraudEvent
from backend.models.publication import Publication
from backend.models.sop_template import SOPTemplate, ABTest

router = APIRouter()


@router.get("/health")
async def system_health(db: AsyncSession = Depends(get_db)):
    """Kiểm tra sức khỏe hệ thống."""
    checks = {}

    # Database
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = {"status": "ok"}
    except Exception as e:
        checks["database"] = {"status": "error", "detail": str(e)}

    # Redis
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.redis_url)
        await r.ping()
        await r.aclose()
        checks["redis"] = {"status": "ok"}
    except Exception as e:
        checks["redis"] = {"status": "error", "detail": str(e)}

    # Claude API
    checks["claude_api"] = {
        "status": "configured" if settings.anthropic_api_key else "not_configured"
    }

    all_ok = all(c.get("status") in ("ok", "configured") for c in checks.values())
    return {
        "status": "healthy" if all_ok else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
    }


@router.get("/stats")
async def system_stats(db: AsyncSession = Depends(get_db)):
    """Thống kê tổng quan hệ thống."""
    campaigns_total = await db.scalar(select(func.count()).select_from(Campaign)) or 0
    campaigns_active = await db.scalar(
        select(func.count()).where(Campaign.status == "active")
    ) or 0

    content_total = await db.scalar(select(func.count()).select_from(ContentPiece)) or 0
    content_published = await db.scalar(
        select(func.count()).where(ContentPiece.status == "published")
    ) or 0

    publications_total = await db.scalar(select(func.count()).select_from(Publication)) or 0
    publications_success = await db.scalar(
        select(func.count()).where(Publication.status == "published")
    ) or 0

    templates_total = await db.scalar(select(func.count()).select_from(SOPTemplate)) or 0
    templates_active = await db.scalar(
        select(func.count()).where(SOPTemplate.is_active.is_(True))
    ) or 0

    ab_tests_running = await db.scalar(
        select(func.count()).where(ABTest.status == "running")
    ) or 0

    fraud_unresolved = await db.scalar(
        select(func.count()).where(FraudEvent.resolved.is_(False))
    ) or 0

    total_ai_cost = await db.scalar(
        select(func.coalesce(func.sum(ContentPiece.estimated_cost_usd), 0))
    ) or 0

    analytics_events = await db.scalar(
        select(func.count()).select_from(AnalyticsEvent)
    ) or 0

    return {
        "campaigns": {"total": campaigns_total, "active": campaigns_active},
        "content": {"total": content_total, "published": content_published},
        "publications": {"total": publications_total, "success": publications_success},
        "templates": {"total": templates_total, "active": templates_active},
        "ab_tests_running": ab_tests_running,
        "fraud_unresolved": fraud_unresolved,
        "total_ai_cost_usd": float(total_ai_cost),
        "analytics_events": analytics_events,
    }


@router.post("/tasks/score-templates")
async def trigger_score_templates(db: AsyncSession = Depends(get_db)):
    """Chạy thủ công: chấm điểm template."""
    from backend.sop_engine.scorer import score_all_templates
    results = await score_all_templates(db)
    return {"status": "done", "scored": len(results)}


@router.post("/tasks/evolve-templates")
async def trigger_evolve_templates(db: AsyncSession = Depends(get_db)):
    """Chạy thủ công: tiến hóa template."""
    from backend.sop_engine.prompt_evolution import auto_evolve_top_templates
    evolved = await auto_evolve_top_templates(db)
    return {"status": "done", "evolved": len(evolved), "names": [t.name for t in evolved]}


@router.post("/tasks/process-scheduled")
async def trigger_process_scheduled():
    """Chạy thủ công: xử lý bài đăng đã lên lịch."""
    from backend.affiliate.publishers.scheduler import process_scheduled_publications
    await process_scheduled_publications()
    return {"status": "done"}


@router.post("/tasks/fraud-scan")
async def trigger_fraud_scan(db: AsyncSession = Depends(get_db)):
    """Chạy thủ công: quét gian lận."""
    from backend.analytics.fraud_detector import FraudDetector
    detector = FraudDetector()
    alerts = await detector.scan_recent(db)
    return {"status": "done", "alerts_found": len(alerts)}
