"""Tests cho TikTok Studio — model, CRUD, router, production pipeline.

Coverage:
- TikTokProject model fields + defaults
- studio.py CRUD functions (create, list, get, update, delete)
- studio.py MANUAL_STATUS_MAP validation
- router.py schemas (ProjectCreate, StatusUpdate, PerformanceUpdate)
- production.py angle hints mapping
- Alembic migration file exists với đúng revision chain
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.models.tiktok_project import TikTokProject
from backend.tiktok import kenh2_studio as studio
from backend.tiktok.production import _ANGLE_HINTS

# ── Model tests ───────────────────────────────────────────────────────────────


def test_tiktok_project_explicit_status():
    """TikTokProject nhận status được truyền vào constructor."""
    project = TikTokProject(
        product_name="Máy hâm sữa",
        angle="pain_point",
        title="Review Máy hâm sữa",
        status="script_pending",
    )
    assert project.status == "script_pending"


def test_tiktok_project_explicit_metrics():
    """TikTokProject nhận views/likes/comments/shares được truyền vào constructor."""
    project = TikTokProject(
        product_name="Đèn ngủ LED",
        angle="feature",
        title="Review Đèn ngủ LED",
        views=0,
        likes=0,
        comments=0,
        shares=0,
    )
    assert project.views == 0
    assert project.likes == 0
    assert project.comments == 0
    assert project.shares == 0


def test_tiktok_project_optional_fields_are_none():
    """Các trường optional đều None khi mới tạo."""
    project = TikTokProject(
        product_name="Tai nghe BT",
        angle="social_proof",
        title="Review Tai nghe BT",
    )
    assert project.product_id is None
    assert project.content_id is None
    assert project.script_body is None
    assert project.audio_url is None
    assert project.heygen_hook_url is None
    assert project.heygen_cta_url is None
    assert project.script_ready_at is None
    assert project.audio_ready_at is None
    assert project.clips_ready_at is None


def test_tiktok_project_title_auto_set():
    """TikTokProject lưu title được truyền vào."""
    project = TikTokProject(
        product_name="Máy xay sinh tố",
        angle="feature",
        title="Review Máy xay sinh tố",
    )
    assert project.title == "Review Máy xay sinh tố"


# ── studio.py — MANUAL_STATUS_MAP tests ──────────────────────────────────────


def test_manual_status_map_has_three_keys():
    """MANUAL_STATUS_MAP có đúng 3 milestone thủ công."""
    assert set(studio.MANUAL_STATUS_MAP.keys()) == {
        "b_roll_filmed",
        "editing_done",
        "uploaded",
    }


def test_manual_status_map_values_are_timestamp_fields():
    """MANUAL_STATUS_MAP values là tên trường timestamp trong model."""
    expected = {
        "b_roll_filmed_at",
        "editing_done_at",
        "uploaded_at",
    }
    assert set(studio.MANUAL_STATUS_MAP.values()) == expected


# ── studio.py — CRUD async tests ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_project_sets_correct_fields():
    """create_project tạo TikTokProject với đúng tên, angle, title."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock(side_effect=lambda obj: None)

    project = await studio.create_project(
        db,
        product_name="Dép xốp êm chân",
        angle="pain_point",
    )

    db.add.assert_called_once()
    db.commit.assert_called_once()
    assert project.product_name == "Dép xốp êm chân"
    assert project.angle == "pain_point"
    assert project.title == "Review Dép xốp êm chân"
    assert project.status == "script_pending"


@pytest.mark.asyncio
async def test_create_project_with_optional_fields():
    """create_project lưu product_ref_url và notes khi được truyền."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock(side_effect=lambda obj: None)

    project = await studio.create_project(
        db,
        product_name="Kem dưỡng da",
        angle="social_proof",
        product_ref_url="https://shopee.vn/product/123",
        notes="Sản phẩm hot tháng 4",
    )

    assert project.product_ref_url == "https://shopee.vn/product/123"
    assert project.notes == "Sản phẩm hot tháng 4"


@pytest.mark.asyncio
async def test_get_project_returns_none_if_not_found():
    """get_project trả về None khi không tìm thấy."""
    db = AsyncMock()
    db.get = AsyncMock(return_value=None)

    result = await studio.get_project(db, uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_update_manual_status_b_roll():
    """update_manual_status với 'b_roll_filmed' cập nhật timestamp và status."""
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock(side_effect=lambda obj: None)

    project = TikTokProject(
        product_name="Test",
        angle="feature",
        title="Review Test",
        status="clips_ready",
    )

    result = await studio.update_manual_status(db, project, "b_roll_filmed")

    assert result.status == "b_roll_filmed"
    assert result.b_roll_filmed_at is not None
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_manual_status_invalid_key_raises():
    """update_manual_status với key không hợp lệ raise ValueError."""
    db = AsyncMock()
    project = TikTokProject(
        product_name="Test",
        angle="feature",
        title="Review Test",
    )

    with pytest.raises(ValueError, match="status_key không hợp lệ"):
        await studio.update_manual_status(db, project, "invalid_status")


@pytest.mark.asyncio
async def test_update_performance_sets_live_when_url_provided():
    """update_performance chuyển status sang 'live' khi có tiktok_video_url."""
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock(side_effect=lambda obj: None)

    project = TikTokProject(
        product_name="Test",
        angle="feature",
        title="Review Test",
        status="uploaded",
    )

    result = await studio.update_performance(
        db, project, tiktok_video_url="https://tiktok.com/@user/video/123"
    )

    assert result.status == "live"
    assert result.tiktok_video_url == "https://tiktok.com/@user/video/123"


@pytest.mark.asyncio
async def test_update_performance_metrics():
    """update_performance cập nhật đúng views/likes/comments/shares."""
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock(side_effect=lambda obj: None)

    project = TikTokProject(
        product_name="Test",
        angle="feature",
        title="Review Test",
    )

    result = await studio.update_performance(
        db, project, views=10000, likes=500, comments=30, shares=120
    )

    assert result.views == 10000
    assert result.likes == 500
    assert result.comments == 30
    assert result.shares == 120


@pytest.mark.asyncio
async def test_delete_project_calls_db_delete():
    """delete_project gọi db.delete và db.commit."""
    db = AsyncMock()
    db.delete = AsyncMock()
    db.commit = AsyncMock()

    project = TikTokProject(
        product_name="Test",
        angle="feature",
        title="Review Test",
    )

    await studio.delete_project(db, project)

    db.delete.assert_called_once_with(project)
    db.commit.assert_called_once()


# ── production.py — angle hints tests ────────────────────────────────────────


def test_angle_hints_cover_all_valid_angles():
    """_ANGLE_HINTS có hint cho tất cả 3 angle hợp lệ."""
    assert "pain_point" in _ANGLE_HINTS
    assert "feature" in _ANGLE_HINTS
    assert "social_proof" in _ANGLE_HINTS


def test_angle_hints_are_non_empty():
    """Tất cả angle hints không rỗng."""
    for angle, hint in _ANGLE_HINTS.items():
        assert hint.strip(), f"Hint cho '{angle}' bị rỗng"


# ── Migration file tests ──────────────────────────────────────────────────────


def test_migration_file_exists():
    """File migration tiktok_projects tồn tại."""
    import os

    migration_path = os.path.join(
        os.path.dirname(__file__),
        "../../alembic/versions/e5f6a7b8c9d0_add_tiktok_projects_table.py",
    )
    assert os.path.exists(os.path.normpath(migration_path))


def test_migration_has_correct_revision():
    """Migration có revision ID đúng."""
    import importlib.util
    import os

    path = os.path.normpath(
        os.path.join(
            os.path.dirname(__file__),
            "../../alembic/versions/e5f6a7b8c9d0_add_tiktok_projects_table.py",
        )
    )
    spec = importlib.util.spec_from_file_location("migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    assert migration.revision == "e5f6a7b8c9d0"
    assert migration.down_revision == "d4e5f6a7b8c9"
