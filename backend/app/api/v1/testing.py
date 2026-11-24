import uuid
from typing import List
from fastapi import APIRouter, Body, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_candidate_profile
from app.core.database import get_async_db
from app.models.candidate import CandidateProfile
from app.schemas.assessment import (
    AssessmentConfigureRequest, AssessmentResponse, AssessmentResultResponse,
    AssessmentStartResponse, AttemptHistoryItem, CandidateAnswerSaveRequest
)
from app.schemas.common import APIResponse
from app.services.assessment_service import AssessmentService
from app.services.question_service import QuestionService
from app.services.testing_suggestions import TestingSuggestionService

router = APIRouter(prefix="/testing", tags=["Testing Mode"])


@router.get("/suggestions", response_model=APIResponse[dict])
async def suggest_testing_topics(
    subject: str | None = Query(default=None, min_length=2, max_length=255),
    candidate_profile: CandidateProfile = Depends(get_current_candidate_profile),
    db: AsyncSession = Depends(get_async_db),
):
    suggestions = await TestingSuggestionService.suggest(db, candidate_profile, subject=subject)
    return APIResponse(data=suggestions, message="Topic recommendations returned with evidence status")


@router.post("/configure", response_model=APIResponse[AssessmentResponse], status_code=status.HTTP_201_CREATED)
async def configure_assessment(
    request: AssessmentConfigureRequest,
    candidate_profile: CandidateProfile = Depends(get_current_candidate_profile),
    db: AsyncSession = Depends(get_async_db)
):
    assessment = await AssessmentService.configure_and_create_assessment(db, request, candidate_profile)
    return APIResponse(data=assessment, message="Assessment configured successfully")


@router.post("/{assessment_id}/start", response_model=APIResponse[AssessmentStartResponse])
async def start_assessment(
    assessment_id: uuid.UUID,
    candidate_profile: CandidateProfile = Depends(get_current_candidate_profile),
    db: AsyncSession = Depends(get_async_db)
):
    attempt_data = await AssessmentService.start_assessment(db, assessment_id, candidate_profile)
    return APIResponse(data=attempt_data, message="Assessment session started")


@router.post("/attempts/{attempt_id}/save-answer", response_model=APIResponse[dict])
async def save_answer(
    attempt_id: uuid.UUID,
    request: CandidateAnswerSaveRequest,
    candidate_profile: CandidateProfile = Depends(get_current_candidate_profile),
    db: AsyncSession = Depends(get_async_db)
):
    result = await AssessmentService.save_answer(db, attempt_id, candidate_profile.id, request)
    return APIResponse(data=result, message="Answer auto-saved")


@router.post("/attempts/{attempt_id}/submit", response_model=APIResponse[AssessmentResultResponse])
async def submit_assessment(
    attempt_id: uuid.UUID,
    candidate_profile: CandidateProfile = Depends(get_current_candidate_profile),
    db: AsyncSession = Depends(get_async_db)
):
    result = await AssessmentService.submit_assessment(db, attempt_id, candidate_profile.id)
    return APIResponse(data=result, message="Assessment submitted and evaluated")


@router.get("/history", response_model=APIResponse[List[AttemptHistoryItem]])
async def get_test_history(
    candidate_profile: CandidateProfile = Depends(get_current_candidate_profile),
    db: AsyncSession = Depends(get_async_db)
):
    history = await AssessmentService.get_history(db, candidate_profile.id)
    return APIResponse(data=history, message="Assessment history retrieved")


@router.get("/attempts/{attempt_id}/results", response_model=APIResponse[AssessmentResultResponse])
async def get_assessment_result(
    attempt_id: uuid.UUID,
    candidate_profile: CandidateProfile = Depends(get_current_candidate_profile),
    db: AsyncSession = Depends(get_async_db),
):
    result = await AssessmentService.get_result(db, attempt_id, candidate_profile.id)
    return APIResponse(data=result, message="Assessment result retrieved")


@router.post("/quiz", response_model=APIResponse[dict])
async def generate_quiz(
    topic: str = Body(..., min_length=1, max_length=255),
    num_questions: int = Body(default=10, ge=1, le=50),
    candidate_profile: CandidateProfile = Depends(get_current_candidate_profile),
    db: AsyncSession = Depends(get_async_db),
):
    quiz = await QuestionService.generate_quiz(db, candidate_profile.id, topic, num_questions)
    return APIResponse(data=quiz, message="Quiz generated successfully")
