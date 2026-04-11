from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.platform_account import PlatformAccount
from backend.schemas.campaign import PlatformAccountCreate, PlatformAccountResponse

router = APIRouter()


@router.post("", response_model=PlatformAccountResponse, status_code=201)
async def register_platform(data: PlatformAccountCreate, db: AsyncSession = Depends(get_db)):
    account = PlatformAccount(**data.model_dump())
    db.add(account)
    await db.flush()
    await db.refresh(account)
    return account


@router.get("", response_model=list[PlatformAccountResponse])
async def list_platforms(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PlatformAccount).order_by(PlatformAccount.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{platform_id}", response_model=PlatformAccountResponse)
async def get_platform(platform_id: UUID, db: AsyncSession = Depends(get_db)):
    account = await db.get(PlatformAccount, platform_id)
    if not account:
        raise HTTPException(status_code=404, detail="Platform account not found")
    return account


@router.post("/{platform_id}/test")
async def test_platform_connection(platform_id: UUID, db: AsyncSession = Depends(get_db)):
    account = await db.get(PlatformAccount, platform_id)
    if not account:
        raise HTTPException(status_code=404, detail="Platform account not found")

    from backend.connectors import get_connector

    connector = get_connector(account.platform)
    try:
        is_connected = await connector.authenticate()
        return {"status": "connected" if is_connected else "failed", "platform": account.platform}
    except Exception as e:
        return {"status": "error", "platform": account.platform, "detail": str(e)}
