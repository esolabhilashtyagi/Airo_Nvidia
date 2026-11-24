import uuid
from typing import Any
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_candidate_profile
from app.core.database import get_async_db
from app.models.candidate import CandidateProfile
from app.schemas.common import APIResponse
from app.schemas.interview import (
    InterviewReportResponse, InterviewRespondRequest,
    InterviewSessionResponse, InterviewSetupRequest
)
from app.services.interview_service import InterviewService
from app.models.interview import MockInterview

router = APIRouter(prefix="/interviews", tags=["AI Mock Interviews"])


@router.get("/history", response_model=APIResponse[list[dict]])
async def interview_history(
    candidate_profile: CandidateProfile = Depends(get_current_candidate_profile),
    db: AsyncSession = Depends(get_async_db),
):
    rows = await InterviewService.get_history(db, candidate_profile.id)
    return APIResponse(data=[{
        "id": row.id, "job_role": row.job_role, "target_company": row.target_company,
        "interview_round": row.interview_round, "status": row.status,
        "evaluation_status": row.evaluation_status, "created_at": row.created_at,
    } for row in rows], message="Interview history retrieved")


@router.get("/{interview_id}", response_model=APIResponse[InterviewSessionResponse])
async def get_interview_session(
    interview_id: uuid.UUID,
    candidate_profile: CandidateProfile = Depends(get_current_candidate_profile),
    db: AsyncSession = Depends(get_async_db),
):
    session = await InterviewService.get_session(db, interview_id, candidate_profile.id)
    return APIResponse(data=session, message="Interview session retrieved")


@router.post("/setup", response_model=APIResponse[InterviewSessionResponse], status_code=status.HTTP_201_CREATED)
async def setup_interview(
    request: InterviewSetupRequest,
    candidate_profile: CandidateProfile = Depends(get_current_candidate_profile),
    db: AsyncSession = Depends(get_async_db)
):
    session = await InterviewService.setup_and_start_interview(db, candidate_profile, request)
    return APIResponse(data=session, message="Mock interview started")


@router.post("/{interview_id}/respond", response_model=APIResponse[Any])
async def respond_to_question(
    interview_id: uuid.UUID,
    request: InterviewRespondRequest,
    candidate_profile: CandidateProfile = Depends(get_current_candidate_profile),
    db: AsyncSession = Depends(get_async_db)
):
    session = await InterviewService.respond_to_question(db, interview_id, candidate_profile.id, request)
    return APIResponse(data=session, message="Response processed")


@router.post("/{interview_id}/conclude", response_model=APIResponse[InterviewReportResponse])
async def conclude_interview(
    interview_id: uuid.UUID,
    candidate_profile: CandidateProfile = Depends(get_current_candidate_profile),
    db: AsyncSession = Depends(get_async_db)
):
    report = await InterviewService.conclude_interview(db, interview_id, candidate_profile.id)
    return APIResponse(data=report, message="Interview concluded and evaluated")


@router.get("/{interview_id}/report", response_model=APIResponse[InterviewReportResponse])
async def get_report(
    interview_id: uuid.UUID,
    candidate_profile: CandidateProfile = Depends(get_current_candidate_profile),
    db: AsyncSession = Depends(get_async_db)
):
    report = await InterviewService.get_report(db, interview_id, candidate_profile.id)
    return APIResponse(data=report, message="Interview report retrieved")
