import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

# Import config trước để lấy DATABASE_URL từ .env
from backend.config import settings
from backend.database import Base
import backend.models  # noqa: F401 - đăng ký tất cả models vào metadata

alembic_config = context.config

if alembic_config.config_file_name is not None:
    fileConfig(alembic_config.config_file_name)

# Inject DATABASE_URL từ settings — không đọc từ alembic.ini
# asyncpg không tương thích với Alembic sync runner → dùng psycopg2/asyncpg tùy mode
def _get_sync_url() -> str:
    """Chuyển asyncpg URL sang psycopg2 cho migration offline mode."""
    url = settings.database_url
    return url.replace("postgresql+asyncpg://", "postgresql://")


target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Chạy migration không cần kết nối DB — sinh ra SQL thuần."""
    context.configure(
        url=_get_sync_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Chạy migration qua async engine (asyncpg)."""
    configuration = {
        "sqlalchemy.url": settings.database_url,
    }
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
