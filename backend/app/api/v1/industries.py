import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_async_db
from app.models.taxonomy import Industry
from app.schemas.common import APIResponse
from app.schemas.taxonomy import IndustryResponse

router = APIRouter(prefix="/industries", tags=["Industries & Roles"])


@router.get("", response_model=APIResponse[List[IndustryResponse]])
async def list_industries(
    db: AsyncSession = Depends(get_async_db)
):
    query = (
        select(Industry)
        .where(Industry.is_active == True)
        .options(
            selectinload(Industry.categories),
            selectinload(Industry.job_roles)
        )
        .order_by(Industry.name.asc())
    )
    result = await db.execute(query)
    industries = result.scalars().all()
    output = [IndustryResponse.model_validate(ind) for ind in industries]
    return APIResponse(data=output, message="Industries listed successfully")


@router.get("/{industry_id}", response_model=APIResponse[IndustryResponse])
async def get_industry_detail(
    industry_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db)
):
    query = (
        select(Industry)
        .where(Industry.id == industry_id)
        .options(
            selectinload(Industry.categories),
            selectinload(Industry.job_roles)
        )
    )
    result = await db.execute(query)
    ind = result.scalar_one_or_none()
    if not ind:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Industry not found")
    return APIResponse(data=IndustryResponse.model_validate(ind), message="Industry details retrieved")
