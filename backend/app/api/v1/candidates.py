from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_async_db
from app.models.user import User
from app.schemas.candidate import CandidateProfileResponse, OnboardingStepRequest
from app.schemas.common import APIResponse
from app.services.candidate_service import CandidateService

router = APIRouter(prefix="/candidates", tags=["Candidates & Onboarding"])


@router.get("/profile", response_model=APIResponse[CandidateProfileResponse])
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    profile = await CandidateService.get_profile(db, current_user.id)
    return APIResponse(data=profile, message="Candidate profile retrieved")


@router.post("/onboarding/step", response_model=APIResponse[CandidateProfileResponse])
async def save_onboarding_step(
    request: OnboardingStepRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    profile = await CandidateService.save_onboarding_step(db, current_user.id, request)
    return APIResponse(data=profile, message=f"Onboarding step {request.step} saved successfully")
