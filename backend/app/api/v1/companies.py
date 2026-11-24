from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.models.candidate import Company
from app.schemas.common import APIResponse
from app.schemas.taxonomy import CompanyResponse

router = APIRouter(prefix="/companies", tags=["Companies"])


@router.get("", response_model=APIResponse[List[CompanyResponse]])
async def search_companies(
    search: str = Query("", max_length=120),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_async_db),
):
    query = select(Company).order_by(Company.name.asc()).limit(limit)
    if search.strip():
        query = query.where(Company.name.ilike(f"%{search.strip()}%"))
    result = await db.execute(query)
    return APIResponse(data=[CompanyResponse.model_validate(company) for company in result.scalars().all()])
