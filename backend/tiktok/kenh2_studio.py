"""TikTok Studio — CRUD cho TikTokProject."""

import logging
import re
import uuid
from datetime import datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.tiktok_project import TikTokProject

logger = logging.getLogger(__name__)

# Các status hợp lệ khi owner tự cập nhật thủ công
MANUAL_STATUS_MAP = {
    "b_roll_filmed": "b_roll_filmed_at",
    "editing_done": "editing_done_at",
    "uploaded": "uploaded_at",
}


async def create_project(
    db: AsyncSession,
    product_name: str,
    angle: str,
    product_id: uuid.UUID | None = None,
    product_ref_url: str | None = None,
    notes: str | None = None,
    channel_type: str = "kenh2_real_review",
) -> TikTokProject:
    """Tạo TikTokProject mới — ban đầu ở trạng thái script_pending."""
    project = TikTokProject(
        product_id=product_id,
        product_name=product_name,
        product_ref_url=product_ref_url,
        angle=angle,
        title=f"Review {product_name}",
        notes=notes,
        status="script_pending",
        channel_type=channel_type,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    logger.info(f"TikTokProject created: {project.id} — {product_name}")
    return project


async def list_projects(
    db: AsyncSession,
    status: str | None = None,
    limit: int = 50,
) -> list[TikTokProject]:
    """Lấy danh sách dự án, tuỳ chọn lọc theo status."""
    query = select(TikTokProject).order_by(TikTokProject.created_at.desc()).limit(limit)
    if status:
        query = query.where(TikTokProject.status == status)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_project(db: AsyncSession, project_id: uuid.UUID) -> TikTokProject | None:
    """Lấy 1 dự án theo ID."""
    return await db.get(TikTokProject, project_id)


async def update_manual_status(
    db: AsyncSession,
    project: TikTokProject,
    status_key: str,
) -> TikTokProject:
    """Cập nhật milestone thủ công: b_roll_filmed | editing_done | uploaded.

    Ghi timestamp tương ứng và chuyển status sang stage mới.
    """
    timestamp_field = MANUAL_STATUS_MAP.get(status_key)
    if not timestamp_field:
        raise ValueError(
            f"status_key không hợp lệ: '{status_key}'. Hợp lệ: {list(MANUAL_STATUS_MAP)}"
        )

    now = datetime.utcnow()
    setattr(project, timestamp_field, now)

    # Derive status từ timestamp_field
    new_status_map = {
        "b_roll_filmed_at": "b_roll_filmed",
        "editing_done_at": "editing",
        "uploaded_at": "uploaded",
    }
    project.status = new_status_map[timestamp_field]
    project.updated_at = now

    await db.commit()
    await db.refresh(project)
    return project


async def update_performance(
    db: AsyncSession,
    project: TikTokProject,
    views: int | None = None,
    likes: int | None = None,
    comments: int | None = None,
    shares: int | None = None,
    tiktok_video_url: str | None = None,
    tiktok_video_id: str | None = None,
) -> TikTokProject:
    """Cập nhật số liệu hiệu suất và URL video TikTok."""
    if views is not None:
        project.views = views
    if likes is not None:
        project.likes = likes
    if comments is not None:
        project.comments = comments
    if shares is not None:
        project.shares = shares
    if tiktok_video_url is not None:
        project.tiktok_video_url = tiktok_video_url
        if project.status == "uploaded":
            project.status = "live"
    if tiktok_video_id is not None:
        project.tiktok_video_id = tiktok_video_id

    project.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(project)
    return project


async def delete_project(db: AsyncSession, project: TikTokProject) -> None:
    """Xoá dự án."""
    await db.delete(project)
    await db.commit()


async def fetch_product_from_url(url: str) -> dict:
    """Cố gắng lấy tên + giá sản phẩm từ URL TikTok Shop (best-effort).

    Trả về dict: { product_name, price_text, success }
    Nếu fetch thất bại → success=False, product_name rỗng để frontend yêu cầu nhập tay.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
    }
    try:
        async with httpx.AsyncClient(
            follow_redirects=True, timeout=10.0, headers=headers
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            html = resp.text

        # og:image — lấy ảnh sản phẩm cho Kling AI
        image_url = ""
        og_img = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html)
        if not og_img:
            og_img = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', html)
        if og_img:
            image_url = og_img.group(1).strip()

        # og:title → title tag fallback
        name = ""
        og_match = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']', html)
        if og_match:
            name = og_match.group(1).strip()
        else:
            title_match = re.search(r"<title>([^<]+)</title>", html, re.IGNORECASE)
            if title_match:
                raw = title_match.group(1).strip()
                # Xoá suffix " | TikTok" hay " - TikTok Shop"
                name = re.sub(r"\s*[|\-–]\s*(TikTok.*|Shop.*)$", "", raw, flags=re.IGNORECASE).strip()

        # Giá (pattern: ₫123.456 hoặc 123.456₫ hoặc 123,456đ)
        price_match = re.search(r"(?:₫|đ)\s*([\d.,]+)|([\d.,]+)\s*(?:₫|đ)", html)
        price_text = ""
        if price_match:
            raw_price = (price_match.group(1) or price_match.group(2) or "").strip()
            price_text = f"₫{raw_price}" if raw_price else ""

        return {"product_name": name, "price_text": price_text, "image_url": image_url, "success": bool(name)}

    except Exception as e:
        logger.warning(f"[fetch_product_from_url] Không lấy được thông tin từ URL: {e}")
        return {"product_name": "", "price_text": "", "image_url": "", "success": False}
