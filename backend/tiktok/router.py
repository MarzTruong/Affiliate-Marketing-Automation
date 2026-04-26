"""TikTok Studio API Router — prefix /api/v1/tiktok-studio."""

import json
import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.tiktok_project import TikTokProject
from backend.tiktok import kenh2_studio as studio

router = APIRouter()


# ── Schemas ────────────────────────────────────────────────────────────────


class ProjectCreate(BaseModel):
    product_name: str
    angle: str  # pain_point | feature | social_proof
    product_id: str | None = None
    product_ref_url: str | None = None
    notes: str | None = None


class ProjectFromUrl(BaseModel):
    url: str
    angle: str  # pain_point | feature | social_proof
    channel_type: str = "kenh2_real_review"  # kenh1_faceless | kenh2_real_review
    notes: str | None = None


class UrlPreviewOut(BaseModel):
    product_name: str
    price_text: str
    success: bool


class ProjectOut(BaseModel):
    id: str
    product_name: str
    product_ref_url: str | None
    angle: str
    channel_type: str
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


class GenerateRequest(BaseModel):
    channel_type: str | None = None  # None = dùng channel_type của project


class StatusUpdate(BaseModel):
    status: str  # b_roll_filmed | editing_done | uploaded


class PerformanceUpdate(BaseModel):
    views: int | None = None
    likes: int | None = None
    comments: int | None = None
    shares: int | None = None
    tiktok_video_url: str | None = None
    tiktok_video_id: str | None = None


class TestTTSRequest(BaseModel):
    text: str = "Xin chào, đây là bài test giọng đọc tiếng Việt."


class TestTTSResponse(BaseModel):
    audio_url: str
    voice_id: str
    model_id: str
    char_count: int
    duration_s: float


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
    body: GenerateRequest = GenerateRequest(),
    db: AsyncSession = Depends(get_db),
):
    """Trigger pipeline: script → audio → clips (chạy background).

    Trả về project ngay lập tức với status hiện tại.
    Background task cập nhật dần từng bước.
    """
    project = await _get_or_404(db, project_id)

    if project.status not in ("script_pending", "script_ready", "audio_ready"):
        raise HTTPException(
            400,
            f"Chỉ trigger được khi status là script_pending, script_ready hoặc audio_ready "
            f"(hiện: {project.status})",
        )

    effective_channel = body.channel_type or project.channel_type
    background_tasks.add_task(_run_production_bg, project_id, effective_channel)
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


@router.post("/preview-url", response_model=UrlPreviewOut)
async def preview_url(data: ProjectFromUrl):
    """Lấy thông tin sản phẩm từ URL (best-effort) — không tạo project."""
    result = await studio.fetch_product_from_url(data.url)
    return result


@router.post("/from-url", response_model=ProjectOut, status_code=201)
async def create_from_url(
    data: ProjectFromUrl,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Tạo dự án từ link TikTok Shop — tự động lấy tên SP từ URL."""
    valid_angles = {"pain_point", "feature", "social_proof"}
    if data.angle not in valid_angles:
        raise HTTPException(400, f"angle không hợp lệ. Hợp lệ: {valid_angles}")

    # Best-effort fetch tên sản phẩm từ URL
    fetched = await studio.fetch_product_from_url(data.url)
    product_name = fetched["product_name"] or "Sản phẩm TikTok Shop"
    price_note = f" | Giá: {fetched['price_text']}" if fetched["price_text"] else ""
    image_note = f" | IMG:{fetched['image_url']}" if fetched.get("image_url") else ""
    merged_notes = ((data.notes or "") + price_note + image_note).strip() or None

    project = await studio.create_project(
        db,
        product_name=product_name,
        angle=data.angle,
        product_ref_url=fetched.get("image_url") or data.url,  # dùng image URL cho Kling nếu có
        notes=merged_notes,
        channel_type=data.channel_type,
    )
    background_tasks.add_task(_run_production_bg, str(project.id), data.channel_type)
    return _to_out(project)


def _parse_tts_body(raw_body: bytes) -> str:
    """Parse request body — chấp nhận cả JSON {"text": "..."} lẫn raw text.

    UX thân thiện cho user non-dev: có thể paste text trực tiếp vào Swagger
    không cần bọc JSON. Nếu body bắt đầu bằng '{' thì thử JSON trước,
    fallback về raw text nếu parse fail.
    """
    if not raw_body:
        return ""
    body_str = raw_body.decode("utf-8", errors="replace").strip()
    if not body_str:
        return ""
    if body_str.startswith("{"):
        try:
            data = json.loads(body_str)
            if isinstance(data, dict) and "text" in data:
                return str(data["text"]).strip()
        except json.JSONDecodeError:
            pass
    return body_str


@router.post(
    "/test-tts",
    response_model=TestTTSResponse,
    openapi_extra={
        "requestBody": {
            "required": True,
            "description": (
                "Gõ text tiếng Việt cần đọc vào đây. Chấp nhận 2 kiểu:\n"
                "- Plain text: `Xin chào, đây là giọng clone.` (dễ nhất)\n"
                '- JSON: `{"text": "Xin chào, đây là giọng clone."}`'
            ),
            "content": {
                "text/plain": {
                    "schema": {"type": "string"},
                    "example": "Xin chào, đây là bài test giọng đọc tiếng Việt.",
                },
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/TestTTSRequest"},
                    "example": {"text": "Xin chào, đây là bài test giọng đọc tiếng Việt."},
                },
            },
        }
    },
)
async def test_tts(request: Request):
    """Test ElevenLabs TTS trực tiếp với text tùy ý — không cần project.

    Dùng để kiểm tra giọng + model trước khi generate video thật.

    **UX note:** Có thể paste **text thuần** hoặc **JSON** đều chạy được.
    Nếu thấy lỗi "Body rỗng" → xóa example mặc định và gõ lại.
    """
    from backend.ai_engine.elevenlabs_engine import (
        ElevenLabsError,
        create_elevenlabs_engine,
    )

    raw_body = await request.body()
    text = _parse_tts_body(raw_body)

    if not text:
        raise HTTPException(
            400,
            "Body rỗng. Gõ text tiếng Việt cần đọc (có thể paste thẳng, không cần bọc JSON).",
        )

    engine = create_elevenlabs_engine()
    await engine.initialize()

    if not engine.is_available():
        raise HTTPException(
            503,
            "ElevenLabs chưa cấu hình. Vào Settings → ElevenLabs → điền API Key và Voice ID.",
        )

    try:
        result = await engine.generate_audio(text=text, filename_prefix="test_tts")
    except ElevenLabsError as e:
        raise HTTPException(400, str(e)) from e

    return TestTTSResponse(
        audio_url=result.audio_url,
        voice_id=result.voice_id,
        model_id=engine.config.model_id,
        char_count=result.char_count,
        duration_s=result.duration_s,
    )


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
        "channel_type": p.channel_type,
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


async def _run_production_bg(
    project_id: str,
    channel_type: str = "kenh2_real_review",
) -> None:
    """Background task wrapper — chạy production pipeline với DB session riêng."""
    from backend.database import get_db_context
    from backend.tiktok.production import run_production

    async with get_db_context() as db:
        try:
            project = await studio.get_project(db, uuid.UUID(project_id))
            if project:
                await run_production(db, project, channel_type=channel_type)
        except Exception as e:
            import logging

            logging.getLogger(__name__).error(
                f"[BackgroundProduction:{project_id}] Lỗi: {e}", exc_info=True
            )
