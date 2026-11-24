from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_candidate_profile, get_current_user
from app.core.database import get_async_db
from app.models.candidate import CandidateProfile
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.dashboard import AnalyticsResponse, DashboardOverviewResponse
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Candidate Dashboard & Analytics"])


@router.get("/overview", response_model=APIResponse[DashboardOverviewResponse])
async def get_dashboard_overview(
    candidate_profile: CandidateProfile = Depends(get_current_candidate_profile),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    overview = await DashboardService.get_overview(db, candidate_profile, current_user)
    return APIResponse(data=overview, message="Dashboard overview retrieved")


@router.get("/analytics", response_model=APIResponse[AnalyticsResponse])
async def get_dashboard_analytics(
    candidate_profile: CandidateProfile = Depends(get_current_candidate_profile),
    db: AsyncSession = Depends(get_async_db)
):
    analytics = await DashboardService.get_analytics(db, candidate_profile.id)
    return APIResponse(data=analytics, message="Analytics data retrieved")
