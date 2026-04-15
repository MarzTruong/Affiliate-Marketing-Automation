"""REST API cho Automation Pipeline."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.automation import AutomationRule, PipelineRun, ScheduledPost
from backend.models.content import ContentPiece

router = APIRouter()


# ── Schemas ────────────────────────────────────────────────────────────────

class AutomationRuleCreate(BaseModel):
    name: str
    platform: str
    category: str | None = None
    min_commission_pct: float | None = None
    min_price: float | None = None
    max_price: float | None = None
    min_rating: float | None = None
    min_sales: int | None = None
    max_products_per_run: int = 5
    keywords: str | None = None
    content_types: dict | None = None
    publish_channels: dict | None = None
    generate_visual: bool = True
    bannerbear_template_id: str | None = None
    cron_expression: str = "0 12,20,22 * * *"


class AutomationRuleOut(BaseModel):
    id: str
    name: str
    platform: str
    category: str | None
    is_active: bool
    cron_expression: str
    min_commission_pct: float | None
    min_price: float | None
    max_price: float | None
    publish_channels: dict | None
    content_types: dict | None
    generate_visual: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PipelineRunOut(BaseModel):
    id: str
    rule_id: str
    status: str
    products_found: int
    products_filtered: int
    content_created: int
    visuals_created: int
    posts_scheduled: int
    started_at: datetime
    finished_at: datetime | None
    error_log: str | None

    model_config = {"from_attributes": True}


class ScheduledPostOut(BaseModel):
    id: str
    content_id: str
    channel: str
    scheduled_at: datetime
    published_at: datetime | None
    status: str
    visual_url: str | None

    model_config = {"from_attributes": True}


class ReviewItemOut(BaseModel):
    """Bài chờ duyệt — gộp ScheduledPost + ContentPiece preview."""
    post_id: str
    content_id: str
    content_title: str | None
    content_body_preview: str
    content_type: str
    channel: str
    scheduled_at: datetime
    visual_url: str | None
    rule_name: str | None
    audio_url: str | None = None
    heygen_hook_url: str | None = None
    heygen_cta_url: str | None = None


class ReviewDecision(BaseModel):
    reason: str | None = None


class ApproveDecision(BaseModel):
    """Body cho approve — user có thể chỉnh sửa nội dung trước khi duyệt."""
    edited_body: str | None = None  # Nếu có → lưu bản chỉnh sửa, signal "edited_then_approved"


class BulkApproveDecision(BaseModel):
    post_ids: list[str]


class BulkRejectDecision(BaseModel):
    post_ids: list[str]
    reason: str | None = None


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.get("", response_model=list[AutomationRuleOut])
async def list_rules(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AutomationRule).order_by(AutomationRule.created_at.desc()))
    rules = result.scalars().all()
    return [_rule_to_out(r) for r in rules]


@router.post("", response_model=AutomationRuleOut, status_code=201)
async def create_rule(data: AutomationRuleCreate, db: AsyncSession = Depends(get_db)):
    from decimal import Decimal
    rule = AutomationRule(
        name=data.name,
        platform=data.platform,
        category=data.category,
        min_commission_pct=Decimal(str(data.min_commission_pct)) if data.min_commission_pct else None,
        min_price=Decimal(str(data.min_price)) if data.min_price else None,
        max_price=Decimal(str(data.max_price)) if data.max_price else None,
        min_rating=Decimal(str(data.min_rating)) if data.min_rating else None,
        min_sales=data.min_sales,
        max_products_per_run=data.max_products_per_run,
        keywords=data.keywords,
        content_types=data.content_types or {"social_post": True},
        publish_channels=data.publish_channels or {"facebook": True},
        generate_visual=data.generate_visual,
        bannerbear_template_id=data.bannerbear_template_id,
        cron_expression=data.cron_expression,
        is_active=True,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return _rule_to_out(rule)


@router.patch("/{rule_id}/toggle", response_model=AutomationRuleOut)
async def toggle_rule(rule_id: str, db: AsyncSession = Depends(get_db)):
    rule = await db.get(AutomationRule, uuid.UUID(rule_id))
    if not rule:
        raise HTTPException(404, "Rule không tồn tại")
    rule.is_active = not rule.is_active
    await db.commit()
    return _rule_to_out(rule)


@router.delete("/{rule_id}", status_code=204)
async def delete_rule(rule_id: str, db: AsyncSession = Depends(get_db)):
    rule = await db.get(AutomationRule, uuid.UUID(rule_id))
    if not rule:
        raise HTTPException(404, "Rule không tồn tại")
    await db.delete(rule)
    await db.commit()


@router.post("/{rule_id}/trigger", response_model=PipelineRunOut)
async def trigger_pipeline(rule_id: str, db: AsyncSession = Depends(get_db)):
    """Trigger pipeline thủ công ngay lập tức."""
    rule = await db.get(AutomationRule, uuid.UUID(rule_id))
    if not rule:
        raise HTTPException(404, "Rule không tồn tại")

    from backend.affiliate.pipeline import run_pipeline
    run = await run_pipeline(db, rule)
    return _run_to_out(run)


@router.get("/{rule_id}/runs", response_model=list[PipelineRunOut])
async def get_pipeline_runs(
    rule_id: str,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PipelineRun)
        .where(PipelineRun.rule_id == uuid.UUID(rule_id))
        .order_by(PipelineRun.started_at.desc())
        .limit(limit)
    )
    return [_run_to_out(r) for r in result.scalars().all()]


@router.get("/scheduled-posts", response_model=list[ScheduledPostOut])
async def get_scheduled_posts(
    status: str | None = None,
    channel: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    query = select(ScheduledPost).order_by(ScheduledPost.scheduled_at)
    if status:
        query = query.where(ScheduledPost.status == status)
    if channel:
        query = query.where(ScheduledPost.channel == channel)
    query = query.limit(limit)
    result = await db.execute(query)
    return [_post_to_out(p) for p in result.scalars().all()]


@router.get("/schedule-insights")
async def get_schedule_insights(db: AsyncSession = Depends(get_db)):
    from backend.affiliate.adaptive_scheduler import get_schedule_insights
    return await get_schedule_insights(db)


@router.get("/review-queue", response_model=list[ReviewItemOut])
async def get_review_queue(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """Danh sách bài đang chờ duyệt (pending_review) từ automation pipeline."""
    result = await db.execute(
        select(ScheduledPost)
        .where(ScheduledPost.status == "pending_review")
        .order_by(ScheduledPost.created_at.desc())
        .limit(limit)
    )
    posts = result.scalars().all()

    items = []
    for post in posts:
        content = await db.get(ContentPiece, post.content_id)
        # Lấy rule name qua pipeline_run
        rule_name = None
        if post.pipeline_run_id:
            run = await db.get(PipelineRun, post.pipeline_run_id)
            if run:
                rule = await db.get(AutomationRule, run.rule_id)
                rule_name = rule.name if rule else None

        body_preview = ""
        if content and content.body:
            body_preview = content.body[:500] + ("…" if len(content.body) > 500 else "")

        items.append({
            "post_id": str(post.id),
            "content_id": str(post.content_id),
            "content_title": content.title if content else None,
            "content_body_preview": body_preview,
            "content_type": content.content_type if content else "social_post",
            "channel": post.channel,
            "scheduled_at": post.scheduled_at,
            "visual_url": post.visual_url,
            "rule_name": rule_name,
            "audio_url": content.audio_url if content else None,
            "heygen_hook_url": content.heygen_hook_url if content else None,
            "heygen_cta_url": content.heygen_cta_url if content else None,
        })
    return items


@router.post("/review/{post_id}/approve", response_model=ScheduledPostOut)
async def approve_post(
    post_id: str,
    body: ApproveDecision = ApproveDecision(),
    db: AsyncSession = Depends(get_db),
):
    """Duyệt bài — chuyển trạng thái pending_review → scheduled.

    Nếu body.edited_body có giá trị: cập nhật ContentPiece.body và lưu vào
    AITrainingData với signal "edited_then_approved".
    Nếu không: lưu bản gốc với signal "approved".
    Cả 2 trường hợp đều tạo 1 bản ghi AITrainingData làm văn mẫu few-shot.
    """
    post = await db.get(ScheduledPost, uuid.UUID(post_id))
    if not post:
        raise HTTPException(404, "Bài đăng không tồn tại")
    if post.status != "pending_review":
        raise HTTPException(400, f"Bài không ở trạng thái chờ duyệt (hiện: {post.status})")

    # Lấy ContentPiece liên quan
    content = await db.get(ContentPiece, post.content_id) if post.content_id else None

    # Xác định final_text và quality_signal
    if body.edited_body and body.edited_body.strip():
        final_text = body.edited_body.strip()
        quality_signal = "edited_then_approved"
        # Cập nhật body trong ContentPiece
        if content:
            content.body = final_text
    else:
        final_text = content.body if content else ""
        quality_signal = "approved"

    # Lưu vào AITrainingData nếu có nội dung
    if final_text and content:
        from backend.models.ai_training_data import AITrainingData
        from backend.models.product import Product

        product = await db.get(Product, content.product_id) if content.product_id else None
        training_record = AITrainingData(
            content_type=content.content_type,
            product_category=product.category if product else "",
            product_platform=product.platform if product else "",
            final_text=final_text,
            quality_signal=quality_signal,
            source_content_id=content.id,
        )
        db.add(training_record)

    post.status = "scheduled"
    await db.commit()
    return _post_to_out(post)


@router.post("/review/{post_id}/reject", status_code=204)
async def reject_post(post_id: str, body: ReviewDecision, db: AsyncSession = Depends(get_db)):
    """Từ chối bài — chuyển trạng thái pending_review → cancelled."""
    post = await db.get(ScheduledPost, uuid.UUID(post_id))
    if not post:
        raise HTTPException(404, "Bài đăng không tồn tại")
    if post.status != "pending_review":
        raise HTTPException(400, f"Bài không ở trạng thái chờ duyệt (hiện: {post.status})")
    post.status = "cancelled"
    if body.reason:
        post.error_message = body.reason[:500]
    await db.commit()


@router.post("/review/bulk-approve")
async def bulk_approve_posts(body: BulkApproveDecision, db: AsyncSession = Depends(get_db)):
    """Duyệt nhiều bài cùng lúc — trả về số bài đã duyệt thành công."""
    approved = 0
    for post_id in body.post_ids:
        try:
            post = await db.get(ScheduledPost, uuid.UUID(post_id))
            if not post or post.status != "pending_review":
                continue
            content = await db.get(ContentPiece, post.content_id) if post.content_id else None
            if content:
                from backend.models.ai_training_data import AITrainingData
                from backend.models.product import Product
                product = await db.get(Product, content.product_id) if content.product_id else None
                db.add(AITrainingData(
                    content_type=content.content_type,
                    product_category=product.category if product else "",
                    product_platform=product.platform if product else "",
                    final_text=content.body or "",
                    quality_signal="approved",
                    source_content_id=content.id,
                ))
            post.status = "scheduled"
            approved += 1
        except Exception:
            continue
    await db.commit()
    return {"approved": approved, "total": len(body.post_ids)}


@router.post("/review/bulk-reject", status_code=204)
async def bulk_reject_posts(body: BulkRejectDecision, db: AsyncSession = Depends(get_db)):
    """Từ chối nhiều bài cùng lúc."""
    for post_id in body.post_ids:
        try:
            post = await db.get(ScheduledPost, uuid.UUID(post_id))
            if not post or post.status != "pending_review":
                continue
            post.status = "cancelled"
            if body.reason:
                post.error_message = body.reason[:500]
        except Exception:
            continue
    await db.commit()


# ── Helpers ────────────────────────────────────────────────────────────────

def _rule_to_out(r: AutomationRule) -> dict:
    return {
        "id": str(r.id),
        "name": r.name,
        "platform": r.platform,
        "category": r.category,
        "is_active": r.is_active,
        "cron_expression": r.cron_expression,
        "min_commission_pct": float(r.min_commission_pct) if r.min_commission_pct else None,
        "min_price": float(r.min_price) if r.min_price else None,
        "max_price": float(r.max_price) if r.max_price else None,
        "publish_channels": r.publish_channels,
        "content_types": r.content_types,
        "generate_visual": r.generate_visual,
        "created_at": r.created_at,
    }


def _run_to_out(r: PipelineRun) -> dict:
    return {
        "id": str(r.id),
        "rule_id": str(r.rule_id),
        "status": r.status,
        "products_found": r.products_found,
        "products_filtered": r.products_filtered,
        "content_created": r.content_created,
        "visuals_created": r.visuals_created,
        "posts_scheduled": r.posts_scheduled,
        "started_at": r.started_at,
        "finished_at": r.finished_at,
        "error_log": r.error_log,
    }


def _post_to_out(p: ScheduledPost) -> dict:
    return {
        "id": str(p.id),
        "content_id": str(p.content_id),
        "channel": p.channel,
        "scheduled_at": p.scheduled_at,
        "published_at": p.published_at,
        "status": p.status,
        "visual_url": p.visual_url,
    }
