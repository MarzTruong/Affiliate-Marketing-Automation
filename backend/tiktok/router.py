"""TikTok Studio API Router — prefix /api/v1/tiktok-studio."""

import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.tiktok_project import TikTokProject
from backend.tiktok import studio

router = APIRouter()


# ── Schemas ────────────────────────────────────────────────────────────────


class ProjectCreate(BaseModel):
    product_name: str
    angle: str  # pain_point | feature | social_proof
    product_id: str | None = None
    product_ref_url: str | None = None
    notes: str | None = None


class ProjectOut(BaseModel):
    id: str
    product_name: str
    product_ref_url: str | None
    angle: str
    title: str
    status: str
    script_body: str | None
    audio_url: str | None
    audio_duration_s: float | None
    heygen_hook_url: str | None
    heygen_cta_url: str | None
    script_ready_at: datetime | None
    audio_ready_at: datetime | None
    clips_ready_at: datetime | None
    b_roll_filmed_at: datetime | None
    editing_done_at: datetime | None
    uploaded_at: datetime | None
    tiktok_video_url: str | None
    views: int
    likes: int
    comments: int
    shares: int
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StatusUpdate(BaseModel):
    status: str  # b_roll_filmed | editing_done | uploaded


class PerformanceUpdate(BaseModel):
    views: int | None = None
    likes: int | None = None
    comments: int | None = None
    shares: int | None = None
    tiktok_video_url: str | None = None
    tiktok_video_id: str | None = None


# ── Endpoints ──────────────────────────────────────────────────────────────


@router.get("", response_model=list[ProjectOut])
async def list_projects(
    status: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """Danh sách dự án TikTok, tuỳ chọn lọc theo status."""
    projects = await studio.list_projects(db, status=status, limit=limit)
    return [_to_out(p) for p in projects]


@router.post("", response_model=ProjectOut, status_code=201)
async def create_project(data: ProjectCreate, db: AsyncSession = Depends(get_db)):
    """Tạo dự án mới — trạng thái ban đầu: script_pending."""
    valid_angles = {"pain_point", "feature", "social_proof"}
    if data.angle not in valid_angles:
        raise HTTPException(400, f"angle không hợp lệ. Hợp lệ: {valid_angles}")

    product_uuid = uuid.UUID(data.product_id) if data.product_id else None
    project = await studio.create_project(
        db,
        product_name=data.product_name,
        angle=data.angle,
        product_id=product_uuid,
        product_ref_url=data.product_ref_url,
        notes=data.notes,
    )
    return _to_out(project)


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    """Lấy chi tiết 1 dự án."""
    project = await _get_or_404(db, project_id)
    return _to_out(project)


@router.post("/{project_id}/generate", response_model=ProjectOut)
async def generate_project(
    project_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Trigger pipeline: script → audio → clips (chạy background).

    Trả về project ngay lập tức với status hiện tại.
    Background task cập nhật dần từng bước.
    """
    project = await _get_or_404(db, project_id)

    if project.status not in ("script_pending", "script_ready"):
        raise HTTPException(
            400,
            f"Chỉ trigger được khi status là script_pending hoặc script_ready "
            f"(hiện: {project.status})",
        )

    background_tasks.add_task(_run_production_bg, project_id)
    return _to_out(project)


@router.patch("/{project_id}/status", response_model=ProjectOut)
async def update_status(
    project_id: str,
    body: StatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Cập nhật milestone thủ công: b_roll_filmed | editing_done | uploaded."""
    project = await _get_or_404(db, project_id)
    try:
        project = await studio.update_manual_status(db, project, body.status)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return _to_out(project)


@router.patch("/{project_id}/performance", response_model=ProjectOut)
async def update_performance(
    project_id: str,
    body: PerformanceUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Cập nhật số liệu hiệu suất và URL video TikTok."""
    project = await _get_or_404(db, project_id)
    project = await studio.update_performance(
        db,
        project,
        views=body.views,
        likes=body.likes,
        comments=body.comments,
        shares=body.shares,
        tiktok_video_url=body.tiktok_video_url,
        tiktok_video_id=body.tiktok_video_id,
    )
    return _to_out(project)


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: str, db: AsyncSession = Depends(get_db)):
    """Xoá dự án."""
    project = await _get_or_404(db, project_id)
    await studio.delete_project(db, project)


# ── Helpers ────────────────────────────────────────────────────────────────


async def _get_or_404(db: AsyncSession, project_id: str) -> TikTokProject:
    try:
        pid = uuid.UUID(project_id)
    except ValueError as e:
        raise HTTPException(400, "project_id không hợp lệ") from e

    project = await studio.get_project(db, pid)
    if not project:
        raise HTTPException(404, "Dự án không tồn tại")
    return project


def _to_out(p: TikTokProject) -> dict:
    return {
        "id": str(p.id),
        "product_name": p.product_name,
        "product_ref_url": p.product_ref_url,
        "angle": p.angle,
        "title": p.title,
        "status": p.status,
        "script_body": p.script_body,
        "audio_url": p.audio_url,
        "audio_duration_s": p.audio_duration_s,
        "heygen_hook_url": p.heygen_hook_url,
        "heygen_cta_url": p.heygen_cta_url,
        "script_ready_at": p.script_ready_at,
        "audio_ready_at": p.audio_ready_at,
        "clips_ready_at": p.clips_ready_at,
        "b_roll_filmed_at": p.b_roll_filmed_at,
        "editing_done_at": p.editing_done_at,
        "uploaded_at": p.uploaded_at,
        "tiktok_video_url": p.tiktok_video_url,
        "views": p.views,
        "likes": p.likes,
        "comments": p.comments,
        "shares": p.shares,
        "notes": p.notes,
        "created_at": p.created_at,
        "updated_at": p.updated_at,
    }


async def _run_production_bg(project_id: str) -> None:
    """Background task wrapper — chạy production pipeline với DB session riêng."""
    from backend.database import get_db_context
    from backend.tiktok.production import run_production

    async with get_db_context() as db:
        try:
            project = await studio.get_project(db, uuid.UUID(project_id))
            if project:
                await run_production(db, project)
        except Exception as e:
            import logging

            logging.getLogger(__name__).error(
                f"[BackgroundProduction:{project_id}] Lỗi: {e}", exc_info=True
            )
