"""APScheduler tích hợp FastAPI.

Jobs định kỳ:
- pipeline_job: chạy automation pipeline theo cron của từng AutomationRule
- weekly_schedule_update: cập nhật lịch dựa trên Adaptive Scheduler
- daily_report_job: gửi báo cáo ngày qua Telegram lúc 22:30
- weekly_report_job: gửi tóm tắt tuần qua Telegram mỗi thứ 2 07:00
- publish_due_posts: đăng các bài đã đến giờ (chạy mỗi phút)
"""

import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

from backend.database import get_db_context

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone="Asia/Ho_Chi_Minh")
    return _scheduler


async def start_scheduler() -> None:
    """Khởi động scheduler — gọi trong FastAPI lifespan."""
    scheduler = get_scheduler()

    # Đăng bài đã đến giờ — chạy mỗi phút
    scheduler.add_job(
        _publish_due_posts,
        IntervalTrigger(minutes=1),
        id="publish_due_posts",
        replace_existing=True,
        name="Đăng bài đã đến giờ",
    )

    # Chạy pipeline rules — mỗi giờ kiểm tra rule nào cần trigger
    scheduler.add_job(
        _check_and_run_pipelines,
        IntervalTrigger(minutes=30),
        id="check_pipelines",
        replace_existing=True,
        name="Kiểm tra và chạy pipeline",
    )

    # Cập nhật lịch từ Adaptive Scheduler — mỗi tuần vào thứ 2 06:00
    scheduler.add_job(
        _weekly_schedule_update,
        CronTrigger(day_of_week="mon", hour=6, minute=0, timezone="Asia/Ho_Chi_Minh"),
        id="weekly_schedule_update",
        replace_existing=True,
        name="Cập nhật lịch đăng thích ứng",
    )

    # Báo cáo ngày — 22:30 mỗi ngày
    scheduler.add_job(
        _daily_report,
        CronTrigger(hour=22, minute=30, timezone="Asia/Ho_Chi_Minh"),
        id="daily_report",
        replace_existing=True,
        name="Báo cáo ngày qua Telegram",
    )

    # Tóm tắt tuần — thứ 2 07:00
    scheduler.add_job(
        _weekly_report,
        CronTrigger(day_of_week="mon", hour=7, minute=0, timezone="Asia/Ho_Chi_Minh"),
        id="weekly_report",
        replace_existing=True,
        name="Tóm tắt tuần qua Telegram",
    )

    # PDF báo cáo tuần — thứ 2 07:05 (sau text report 5 phút)
    scheduler.add_job(
        _weekly_pdf_report,
        CronTrigger(day_of_week="mon", hour=7, minute=5, timezone="Asia/Ho_Chi_Minh"),
        id="weekly_pdf_report",
        replace_existing=True,
        name="PDF báo cáo tuần qua Telegram",
    )

    scheduler.start()
    logger.info("Scheduler khởi động — timezone: Asia/Ho_Chi_Minh")


async def stop_scheduler() -> None:
    """Dừng scheduler — gọi trong FastAPI shutdown."""
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler đã dừng")


async def trigger_rule_now(rule_id: str) -> None:
    """Trigger thủ công 1 rule ngay lập tức (từ API hoặc CBD chat)."""
    from backend.affiliate.pipeline import run_pipeline

    async with get_db_context() as db:
        from backend.models.automation import AutomationRule

        result = await db.execute(select(AutomationRule).where(AutomationRule.id == rule_id))
        rule = result.scalar_one_or_none()
        if rule:
            await run_pipeline(db, rule)


# ── Internal job functions ─────────────────────────────────────────────────


async def _publish_due_posts() -> None:
    """Đăng tất cả ScheduledPost đã đến giờ."""
    from backend.affiliate.publisher import publish_scheduled_post
    from backend.models.automation import ScheduledPost

    async with get_db_context() as db:
        now = datetime.utcnow()
        result = await db.execute(
            select(ScheduledPost).where(
                ScheduledPost.status == "scheduled",
                ScheduledPost.scheduled_at <= now,
            )
        )
        due_posts = result.scalars().all()

        for post in due_posts:
            try:
                await publish_scheduled_post(db, post)
            except Exception as e:
                logger.error(f"Lỗi đăng bài {post.id}: {e}")
                post.status = "failed"
                post.error_message = str(e)[:500]
        await db.commit()


async def _check_and_run_pipelines() -> None:
    """Kiểm tra AutomationRule nào cần chạy dựa trên cron expression."""
    from croniter import croniter  # type: ignore[import-untyped]

    from backend.affiliate.pipeline import run_pipeline
    from backend.models.automation import AutomationRule, PipelineRun

    async with get_db_context() as db:
        result = await db.execute(select(AutomationRule).where(AutomationRule.is_active == True))
        rules = result.scalars().all()
        now = datetime.now()

        for rule in rules:
            try:
                cron = croniter(rule.cron_expression, now)
                # Kiểm tra nếu giờ hiện tại khớp với cron (trong 30 phút tới)
                prev_run = cron.get_prev(datetime)
                minutes_ago = (now - prev_run).total_seconds() / 60
                if minutes_ago <= 30:
                    # Kiểm tra chưa chạy trong 30 phút này
                    recent = await db.execute(
                        select(PipelineRun).where(
                            PipelineRun.rule_id == rule.id,
                            PipelineRun.started_at >= prev_run,
                        )
                    )
                    if not recent.scalar_one_or_none():
                        logger.info(f"Chạy pipeline rule: {rule.name}")
                        await run_pipeline(db, rule)
            except Exception as e:
                logger.error(f"Lỗi kiểm tra rule {rule.name}: {e}")


async def _weekly_schedule_update() -> None:
    """Cập nhật cron expression cho tất cả rules dựa trên Adaptive Scheduler."""
    from backend.affiliate.adaptive_scheduler import update_rule_schedule
    from backend.models.automation import AutomationRule

    async with get_db_context() as db:
        result = await db.execute(select(AutomationRule).where(AutomationRule.is_active == True))
        rules = result.scalars().all()

        for rule in rules:
            old_cron = rule.cron_expression
            new_cron = await update_rule_schedule(db, rule)
            if old_cron != new_cron:
                logger.info(f"Cập nhật lịch '{rule.name}': {old_cron} → {new_cron}")

        logger.info(f"Đã cập nhật lịch cho {len(rules)} rules")


async def _daily_report() -> None:
    from backend.reports.telegram_reporter import send_daily_report

    async with get_db_context() as db:
        await send_daily_report(db)


async def _weekly_report() -> None:
    from backend.reports.telegram_reporter import send_weekly_report

    async with get_db_context() as db:
        await send_weekly_report(db)


async def _weekly_pdf_report() -> None:
    from backend.reports.telegram_reporter import send_weekly_pdf_report

    async with get_db_context() as db:
        await send_weekly_pdf_report(db)
