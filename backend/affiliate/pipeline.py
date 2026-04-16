"""Pipeline Orchestrator — điều phối toàn bộ automation pipeline.

Flow:
scan products → filter → create DB products → generate AI content
→ generate visual → schedule posts → notify Telegram

Mỗi lần chạy tạo 1 PipelineRun để tracking lịch sử.
"""

import logging
import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.automation import AutomationRule, PipelineRun, ScheduledPost
from backend.models.campaign import Campaign
from backend.models.content import ContentPiece

logger = logging.getLogger(__name__)


async def run_pipeline(db: AsyncSession, rule: AutomationRule) -> PipelineRun:
    """Chạy toàn bộ pipeline cho 1 AutomationRule."""

    run = PipelineRun(
        rule_id=rule.id,
        status="running",
        started_at=datetime.utcnow(),
    )
    db.add(run)
    await db.flush()  # Lấy ID trước

    details: dict = {"rule_name": rule.name, "platform": rule.platform, "steps": []}

    try:
        # ── Step 1: Scan + Filter sản phẩm ─────────────────────────────
        from backend.affiliate.product_scanner import scan_products

        products, total_found = await scan_products(rule)

        run.products_found = total_found
        run.products_filtered = len(products)
        details["steps"].append({"step": "scan", "found": total_found, "filtered": len(products)})
        logger.info(f"[Pipeline:{rule.name}] Tìm {total_found} SP, lọc được {len(products)}")

        if not products:
            run.status = "completed"
            run.finished_at = datetime.utcnow()
            run.run_details = {**details, "note": "Không có sản phẩm đạt tiêu chí"}
            await db.commit()
            return run

        # ── Step 2: Tạo hoặc lấy Campaign cho rule này ─────────────────
        campaign = await _get_or_create_campaign(db, rule)

        # ── Step 3: Tạo DB Products + AI Content + Visuals ─────────────
        content_ids: list[uuid.UUID] = []
        visual_urls: dict[str, str] = {}
        visual_failures: int = 0
        content_failures: int = 0

        from backend.affiliate.visual_generator import generate_visual
        from backend.ai_engine.content_generator import ContentGenerator
        from backend.models.product import Product as DBProduct

        generator = ContentGenerator()
        content_types = _get_enabled_content_types(rule)

        for prod_info in products:
            # Tạo Product trong DB
            db_product = DBProduct(
                campaign_id=campaign.id,
                name=prod_info.name,
                original_url=prod_info.original_url,
                affiliate_url=prod_info.affiliate_url,
                price=prod_info.price,
                category=prod_info.category,
                platform=rule.platform,
                metadata_json={
                    "description": prod_info.description,
                    "image_url": prod_info.image_url,
                    "image_urls": prod_info.image_urls
                    or ([prod_info.image_url] if prod_info.image_url else []),
                    "commission_rate": prod_info.commission_rate,
                    "rating": prod_info.rating,
                    "sales_count": prod_info.sales_count,
                    "original_price": prod_info.original_price,
                },
            )
            db.add(db_product)
            await db.flush()

            # Tạo Visual — non-critical, track failures để báo cáo
            if rule.generate_visual:
                try:
                    vis_url = await generate_visual(prod_info, rule.bannerbear_template_id)
                    if vis_url:
                        visual_urls[str(db_product.id)] = vis_url
                        run.visuals_created += 1
                except Exception as e:
                    visual_failures += 1
                    logger.error(
                        f"[Pipeline:{rule.name}] Tạo visual thất bại cho {prod_info.name}: {e}",
                        exc_info=True,
                    )

            # Tạo AI Content cho mỗi loại — non-critical per-item, track failures
            for ct in content_types:
                try:
                    piece = await generator.generate(
                        product_id=db_product.id,
                        campaign_id=campaign.id,
                        content_type=ct,
                        db=db,
                    )
                    content_ids.append(piece.id)
                    run.content_created += 1
                except Exception as e:
                    content_failures += 1
                    logger.error(
                        f"[Pipeline:{rule.name}] Tạo content {ct} thất bại cho "
                        f"{prod_info.name}: {e}",
                        exc_info=True,
                    )

        details["steps"].append(
            {
                "step": "content",
                "content_created": run.content_created,
                "content_failures": content_failures,
                "visuals_created": run.visuals_created,
                "visual_failures": visual_failures,
            }
        )

        # Cảnh báo nếu tỷ lệ fail cao — không block pipeline nhưng surface ra report
        if content_failures > 0 and run.content_created == 0:
            logger.error(
                f"[Pipeline:{rule.name}] Tất cả {content_failures} content generation fail — "
                "pipeline sẽ không có bài nào để đăng"
            )

        # ── Step 4: Lên lịch đăng bài ───────────────────────────────────
        from backend.affiliate.adaptive_scheduler import get_best_slots, next_scheduled_time

        channels = _get_enabled_channels(rule)

        for content_id in content_ids:
            for channel in channels:
                # Xác định content_type cho slot này
                content_result = await db.get(ContentPiece, content_id)
                ct = content_result.content_type if content_result else "social_post"

                best_hours = await get_best_slots(db, channel, ct, n=3)
                scheduled_time = next_scheduled_time(best_hours)

                vis_url = visual_urls.get(str(content_id))
                post = ScheduledPost(
                    content_id=content_id,
                    pipeline_run_id=run.id,
                    channel=channel,
                    scheduled_at=scheduled_time,
                    visual_url=vis_url,
                    status="pending_review",
                )
                db.add(post)
                run.posts_scheduled += 1

        details["steps"].append(
            {
                "step": "schedule",
                "posts_scheduled": run.posts_scheduled,
                "channels": channels,
            }
        )

        run.status = "completed"
        run.finished_at = datetime.utcnow()
        run.run_details = details
        await db.commit()

        logger.info(
            f"[Pipeline:{rule.name}] ✅ Hoàn thành — "
            f"{run.products_filtered} SP, {run.content_created} bài, "
            f"{run.posts_scheduled} lịch đăng"
        )

        # ── Step 5: Thông báo Telegram ────────────────────────────────
        await _notify_pipeline_done(run)

    except Exception as e:
        logger.error(f"[Pipeline:{rule.name}] ❌ Lỗi: {e}", exc_info=True)
        run.status = "failed"
        run.error_log = str(e)[:2000]
        run.finished_at = datetime.utcnow()
        run.run_details = details
        await db.commit()

    return run


async def _get_or_create_campaign(db: AsyncSession, rule: AutomationRule) -> Campaign:
    """Lấy campaign hiện tại của rule hoặc tạo mới."""
    from sqlalchemy import select

    result = await db.execute(
        select(Campaign).where(
            Campaign.name == f"[Auto] {rule.name}",
            Campaign.platform == rule.platform,
        )
    )
    campaign = result.scalar_one_or_none()

    if not campaign:
        campaign = Campaign(
            name=f"[Auto] {rule.name}",
            platform=rule.platform,
            status="active",
            target_category=rule.category,
            config={"automation_rule_id": str(rule.id)},
        )
        db.add(campaign)
        await db.flush()

    return campaign


def _get_enabled_content_types(rule: AutomationRule) -> list[str]:
    """Lấy danh sách content type được bật trong rule."""
    default = ["social_post"]
    if not rule.content_types:
        return default
    return [ct for ct, enabled in rule.content_types.items() if enabled] or default


def _get_enabled_channels(rule: AutomationRule) -> list[str]:
    """Lấy danh sách kênh đăng được bật."""
    default = ["facebook"]
    if not rule.publish_channels:
        return default
    return [ch for ch, enabled in rule.publish_channels.items() if enabled] or default


async def _notify_pipeline_done(run: PipelineRun) -> None:
    """Gửi thông báo Telegram khi pipeline hoàn thành."""
    try:
        from backend.reports.telegram_reporter import send_pipeline_report

        await send_pipeline_report(run)
    except Exception as e:
        logger.warning(f"Gửi Telegram notification thất bại: {e}")
