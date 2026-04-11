from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.content import ContentPiece
from backend.schemas.content import ContentGenerateRequest, ContentResponse

router = APIRouter()


@router.post("/generate", response_model=list[ContentResponse], status_code=201)
async def generate_content(data: ContentGenerateRequest, db: AsyncSession = Depends(get_db)):
    from backend.ai_engine.content_generator import ContentGenerator

    generator = ContentGenerator()
    results = []

    for product_id in data.product_ids:
        content_piece = await generator.generate(
            product_id=product_id,
            campaign_id=data.campaign_id,
            content_type=data.content_type,
            template_id=data.template_id,
            db=db,
        )
        results.append(content_piece)

    return results


@router.get("", response_model=list[ContentResponse])
async def list_content(
    campaign_id: UUID | None = None,
    content_type: str | None = None,
    status: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(ContentPiece).offset(skip).limit(limit).order_by(
        ContentPiece.created_at.desc()
    )
    if campaign_id:
        query = query.where(ContentPiece.campaign_id == campaign_id)
    if content_type:
        query = query.where(ContentPiece.content_type == content_type)
    if status:
        query = query.where(ContentPiece.status == status)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{content_id}", response_model=ContentResponse)
async def get_content(content_id: UUID, db: AsyncSession = Depends(get_db)):
    content = await db.get(ContentPiece, content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    return content


@router.post("/{content_id}/regenerate", response_model=ContentResponse)
async def regenerate_content(
    content_id: UUID,
    template_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
):
    content = await db.get(ContentPiece, content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    from backend.ai_engine.content_generator import ContentGenerator

    generator = ContentGenerator()
    new_content = await generator.generate(
        product_id=content.product_id,
        campaign_id=content.campaign_id,
        content_type=content.content_type,
        template_id=template_id,
        db=db,
    )
    return new_content
