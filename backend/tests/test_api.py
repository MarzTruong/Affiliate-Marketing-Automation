"""API integration tests using FastAPI TestClient."""

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.database import Base, get_db
from backend.main import app

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def test_app():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# ── Health ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_health_check(test_app):
    resp = await test_app.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


# ── Campaigns ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_campaign(test_app):
    resp = await test_app.post(
        "/api/v1/campaigns",
        json={
            "name": "Test Campaign",
            "platform": "shopee",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Campaign"
    assert data["status"] == "draft"
    assert data["id"] is not None


@pytest.mark.asyncio
async def test_list_campaigns(test_app):
    # Create one first
    await test_app.post("/api/v1/campaigns", json={"name": "C1", "platform": "shopee"})
    await test_app.post("/api/v1/campaigns", json={"name": "C2", "platform": "tiktok_shop"})

    resp = await test_app.get("/api/v1/campaigns")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 2


@pytest.mark.asyncio
async def test_get_campaign(test_app):
    create_resp = await test_app.post(
        "/api/v1/campaigns", json={"name": "C3", "platform": "tiktok_shop"}
    )
    campaign_id = create_resp.json()["id"]

    resp = await test_app.get(f"/api/v1/campaigns/{campaign_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "C3"


@pytest.mark.asyncio
async def test_get_campaign_not_found(test_app):
    fake_id = str(uuid.uuid4())
    resp = await test_app.get(f"/api/v1/campaigns/{fake_id}")
    assert resp.status_code == 404


# ── Platforms ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_platforms(test_app):
    resp = await test_app.get("/api/v1/platforms")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_register_platform(test_app):
    resp = await test_app.post(
        "/api/v1/platforms",
        json={
            "platform": "shopee",
            "account_name": "My Shopee Store",
            "credentials": {"partner_id": "123", "key": "abc"},
        },
    )
    assert resp.status_code == 201
    assert resp.json()["platform"] == "shopee"


# ── Publisher ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_channels(test_app):
    resp = await test_app.get("/api/v1/publisher/channels")
    assert resp.status_code == 200
    data = resp.json()
    assert "facebook" in data["channels"]
    assert "wordpress" in data["channels"]
    assert "telegram" in data["channels"]


@pytest.mark.asyncio
async def test_list_publications(test_app):
    resp = await test_app.get("/api/v1/publisher/publications")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ── Analytics ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_analytics_overview(test_app):
    resp = await test_app.get("/api/v1/analytics/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_clicks" in data
    assert "total_revenue" in data


@pytest.mark.asyncio
async def test_analytics_daily(test_app):
    resp = await test_app.get("/api/v1/analytics/daily")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_analytics_by_platform(test_app):
    resp = await test_app.get("/api/v1/analytics/by-platform")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_analytics_export_csv(test_app):
    resp = await test_app.get("/api/v1/analytics/export")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_analytics_costs(test_app):
    resp = await test_app.get("/api/v1/analytics/costs")
    assert resp.status_code == 200


# ── SOP ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_template(test_app):
    resp = await test_app.post(
        "/api/v1/sop/templates",
        json={
            "name": "SEO Article V1",
            "content_type": "seo_article",
            "prompt_template": "Viết bài SEO cho {{ product_name }}",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "SEO Article V1"


@pytest.mark.asyncio
async def test_list_templates(test_app):
    await test_app.post(
        "/api/v1/sop/templates",
        json={
            "name": "T1",
            "content_type": "seo_article",
            "prompt_template": "X",
        },
    )
    resp = await test_app.get("/api/v1/sop/templates")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_score_all(test_app):
    resp = await test_app.post("/api/v1/sop/score-all")
    assert resp.status_code == 200


# ── Notifications ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_notifications(test_app):
    resp = await test_app.get("/api/v1/notifications")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_unread_count(test_app):
    resp = await test_app.get("/api/v1/notifications/unread-count")
    assert resp.status_code == 200
    assert resp.json()["unread"] >= 0


@pytest.mark.asyncio
async def test_mark_all_read(test_app):
    resp = await test_app.post("/api/v1/notifications/read-all")
    assert resp.status_code == 200


# ── System ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_system_stats(test_app):
    resp = await test_app.get("/api/v1/system/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "campaigns" in data
    assert "content" in data
    assert "templates" in data
