"""SOP engine API endpoints: templates, A/B tests, scoring, evolution."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.sop_template import ABTest, SOPTemplate
from backend.schemas.sop import (
    ABTestCreate,
    ABTestEvent,
    ABTestResponse,
    EvolveRequest,
    ScoreResponse,
    TemplateCreate,
    TemplateResponse,
)
from backend.sop_engine.ab_testing import (
    conclude_test_manually,
    create_ab_test,
    pick_variant,
    record_conversion,
    record_impression,
)
from backend.sop_engine.prompt_evolution import evolve_template
from backend.sop_engine.scorer import score_all_templates

router = APIRouter()


# ── Templates ──────────────────────────────────────────────────


@router.post("/templates", response_model=TemplateResponse)
async def create_template(req: TemplateCreate, db: AsyncSession = Depends(get_db)):
    """Tạo template SOP mới."""
    tmpl = SOPTemplate(
        id=uuid.uuid4(),
        name=req.name,
        content_type=req.content_type,
        prompt_template=req.prompt_template,
        variables=req.variables,
    )
    db.add(tmpl)
    await db.commit()
    await db.refresh(tmpl)
    return tmpl


@router.get("/templates", response_model=list[TemplateResponse])
async def list_templates(
    content_type: str | None = None,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """Danh sách template SOP."""
    stmt = select(SOPTemplate).order_by(SOPTemplate.performance_score.desc())
    if content_type:
        stmt = stmt.where(SOPTemplate.content_type == content_type)
    if active_only:
        stmt = stmt.where(SOPTemplate.is_active.is_(True))
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/templates/{template_id}", response_model=TemplateResponse)
async def get_template(template_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Chi tiết template."""
    tmpl = await db.get(SOPTemplate, template_id)
    if not tmpl:
        raise HTTPException(404, "Template không tồn tại")
    return tmpl


@router.patch("/templates/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: uuid.UUID,
    name: str | None = None,
    is_active: bool | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Cập nhật template (tên, trạng thái)."""
    tmpl = await db.get(SOPTemplate, template_id)
    if not tmpl:
        raise HTTPException(404, "Template không tồn tại")
    if name is not None:
        tmpl.name = name
    if is_active is not None:
        tmpl.is_active = is_active
    await db.commit()
    await db.refresh(tmpl)
    return tmpl


# ── Scoring ────────────────────────────────────────────────────


@router.post("/score-all", response_model=list[ScoreResponse])
async def rescore_all_templates(
    lookback_days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """Chấm điểm lại tất cả template dựa trên dữ liệu analytics."""
    results = await score_all_templates(db, lookback_days)
    return results


# ── A/B Testing ────────────────────────────────────────────────


@router.post("/ab-tests", response_model=ABTestResponse)
async def create_test(req: ABTestCreate, db: AsyncSession = Depends(get_db)):
    """Tạo A/B test mới giữa hai template."""
    try:
        test = await create_ab_test(
            db, req.campaign_id, req.template_a_id, req.template_b_id, req.sample_size_target
        )
        return test
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/ab-tests", response_model=list[ABTestResponse])
async def list_ab_tests(
    status: str | None = None,
    campaign_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Danh sách A/B test."""
    stmt = select(ABTest).order_by(ABTest.started_at.desc())
    if status:
        stmt = stmt.where(ABTest.status == status)
    if campaign_id:
        stmt = stmt.where(ABTest.campaign_id == campaign_id)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/ab-tests/{test_id}", response_model=ABTestResponse)
async def get_ab_test(test_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Chi tiết A/B test."""
    test = await db.get(ABTest, test_id)
    if not test:
        raise HTTPException(404, "A/B test không tồn tại")
    return test


@router.post("/ab-tests/{test_id}/impression")
async def track_impression(test_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Ghi nhận impression cho A/B test (tự chọn variant)."""
    variant = await pick_variant(db, test_id)
    await record_impression(db, test_id, variant)
    return {"variant": variant}


@router.post("/ab-tests/{test_id}/conversion")
async def track_conversion(req: ABTestEvent, db: AsyncSession = Depends(get_db)):
    """Ghi nhận conversion cho một variant."""
    await record_conversion(db, req.test_id, req.variant)
    return {"status": "recorded"}


@router.post("/ab-tests/{test_id}/conclude", response_model=ABTestResponse)
async def force_conclude(test_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Kết thúc A/B test thủ công."""
    try:
        test = await conclude_test_manually(db, test_id)
        return test
    except ValueError as e:
        raise HTTPException(400, str(e))


# ── Prompt Evolution ───────────────────────────────────────────


@router.post("/evolve", response_model=TemplateResponse)
async def evolve(req: EvolveRequest, db: AsyncSession = Depends(get_db)):
    """Tạo phiên bản cải tiến của template bằng AI."""
    try:
        new_tmpl = await evolve_template(db, req.template_id)
        return new_tmpl
    except ValueError as e:
        raise HTTPException(404, str(e))
    except RuntimeError as e:
        raise HTTPException(429, str(e))
