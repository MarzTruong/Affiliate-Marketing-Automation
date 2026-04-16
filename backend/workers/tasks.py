"""Background tasks for the automation pipeline.

These tasks run periodically via ARQ (async Redis queue) or can be triggered manually.
Pipeline: Score templates -> Evolve top performers -> Auto-publish scheduled content.
"""

import logging
from datetime import datetime, timezone

from arq.cron import cron

from backend.affiliate.publishers.scheduler import process_scheduled_publications
from backend.analytics.fraud_detector import FraudDetector
from backend.database import get_db_context
from backend.sop_engine.prompt_evolution import auto_evolve_top_templates
from backend.sop_engine.scorer import score_all_templates

logger = logging.getLogger(__name__)


async def task_score_templates(ctx: dict | None = None):
    """Chấm điểm lại tất cả template (chạy mỗi 6 giờ)."""
    logger.info("Running: score_all_templates")
    async with get_db_context() as db:
        results = await score_all_templates(db, lookback_days=30)
        logger.info("Scored %d templates", len(results))
    return {"scored": len(results)}


async def task_evolve_templates(ctx: dict | None = None):
    """Tự động tiến hóa template tốt nhất (chạy mỗi ngày)."""
    logger.info("Running: auto_evolve_top_templates")
    async with get_db_context() as db:
        evolved = await auto_evolve_top_templates(db, min_score=50.0, min_usage=10)
        logger.info("Evolved %d templates", len(evolved))
    return {"evolved": len(evolved)}


async def task_process_scheduled(ctx: dict | None = None):
    """Xử lý bài đăng đã lên lịch (chạy mỗi phút)."""
    logger.info("Running: process_scheduled_publications")
    await process_scheduled_publications()
    return {"status": "done"}


async def task_fraud_scan(ctx: dict | None = None):
    """Quét phát hiện gian lận (chạy mỗi 30 phút)."""
    logger.info("Running: fraud_scan")
    async with get_db_context() as db:
        detector = FraudDetector()
        alerts = await detector.scan_recent(db)
        logger.info("Fraud scan: %d alerts", len(alerts))
    return {"alerts": len(alerts)}


# ARQ worker settings
class WorkerSettings:
    """ARQ worker configuration."""

    functions = [
        task_score_templates,
        task_evolve_templates,
        task_process_scheduled,
        task_fraud_scan,
    ]

    cron_jobs = [
        cron(task_score_templates, hour={0, 6, 12, 18}),
        cron(task_evolve_templates, hour=3),
        cron(task_process_scheduled, minute=set(range(60))),
        cron(task_fraud_scan, minute={0, 30}),
    ]

    redis_settings = None  # Will be set from config at runtime

    @staticmethod
    async def on_startup(ctx: dict):
        logger.info("ARQ worker started at %s", datetime.now(timezone.utc))

    @staticmethod
    async def on_shutdown(ctx: dict):
        logger.info("ARQ worker shutting down")
