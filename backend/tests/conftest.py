import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.database import Base

# Use in-memory SQLite for tests
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db(db_engine):
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.fixture
def sample_product_data():
    return {
        "name": "Áo Thun Nam Cotton Premium",
        "price": 199000,
        "category": "thoi_trang",
        "platform": "shopee",
        "original_url": "https://shopee.vn/product/123/456",
        "description": "Áo thun nam chất liệu cotton 100%, thoáng mát, nhiều màu sắc",
    }


@pytest.fixture
def sample_campaign_data():
    return {
        "name": "Shopee Fashion Q2 2026",
        "platform": "shopee",
        "budget_daily": 50.00,
        "target_category": "thoi_trang",
    }


@pytest.fixture
def random_uuid():
    return uuid.uuid4()
