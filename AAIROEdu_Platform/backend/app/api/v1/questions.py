import uuid
from typing import List, Literal, Optional
from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_candidate_profile, require_role
from app.core.database import get_async_db
from app.models.candidate import CandidateProfile
from app.models.question import ApprovalStatus, DifficultyLevel, QuestionType, SourceProvenance
from app.models.user import UserRole
from app.schemas.common import APIResponse, PaginationMeta
from app.schemas.question import (
    CandidateQuestionResponse, ManagedQuestionResponse, PracticeHistoryItem,
    QuestionCreate, QuestionDraftRequest, QuestionPracticeRequest, QuestionPracticeResponse, QuestionUpdate,
)
from app.services.question_service import QuestionService

router = APIRouter(prefix="/questions", tags=["Centralized Question Bank"])


class QuestionReviewRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    comment: Optional[str] = Field(default=None, max_length=4000)


@router.get("/manage", response_model=APIResponse[List[ManagedQuestionResponse]])
async def manage_questions(
    page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100),
    workflow_status: Optional[Literal["draft", "pending_review", "approved", "published", "rejected", "archived", "superseded"]] = None,
    provenance: Optional[SourceProvenance] = None, industry_id: Optional[uuid.UUID] = None,
    search: Optional[str] = Query(None, max_length=200),
    sort_by: Literal["updated_at", "created_at", "difficulty", "subject", "topic", "workflow_status"] = "updated_at",
    sort_order: Literal["asc", "desc"] = "desc",
    _auth=Depends(require_role([UserRole.ADMINISTRATOR, UserRole.CONTENT_MANAGER])), db: AsyncSession = Depends(get_async_db),
):
    rows, total = await QuestionService.manage_questions(db, page, limit, workflow_status, provenance, industry_id, search, sort_by, sort_order)
    return APIResponse(data=rows, meta=PaginationMeta(page=page, limit=limit, total=total, total_pages=(total + limit - 1) // limit), message="Question content retrieved")


@router.post("/manage/ai-draft", response_model=APIResponse[ManagedQuestionResponse], status_code=status.HTTP_201_CREATED)
async def ai_question_draft(request: QuestionDraftRequest,
    actor=Depends(require_role([UserRole.ADMINISTRATOR, UserRole.CONTENT_MANAGER])), db: AsyncSession = Depends(get_async_db)):
    row = await QuestionService.generate_question_draft(db, request, actor.id)
    return APIResponse(data=row, message="AI-generated draft saved for human review")


@router.post("/manage/{question_id}/review", response_model=APIResponse[ManagedQuestionResponse])
async def review_question(question_id: uuid.UUID, request: QuestionReviewRequest,
    actor=Depends(require_role([UserRole.ADMINISTRATOR, UserRole.CONTENT_MANAGER])), db: AsyncSession = Depends(get_async_db)):
    row = await QuestionService.decide_question(db, question_id, ApprovalStatus(request.decision), actor.id, request.comment)
    return APIResponse(data=row, message="Question review decision saved")


@router.post("/manage/{question_id}/submit", response_model=APIResponse[ManagedQuestionResponse])
async def submit_question_for_review(question_id: uuid.UUID,
    _auth=Depends(require_role([UserRole.ADMINISTRATOR, UserRole.CONTENT_MANAGER])), db: AsyncSession = Depends(get_async_db)):
    row = await QuestionService.submit_question_for_review(db, question_id)
    return APIResponse(data=row, message="Draft submitted for review")


@router.post("/manage/{question_id}/publish", response_model=APIResponse[ManagedQuestionResponse])
async def publish_question(question_id: uuid.UUID, _auth=Depends(require_role([UserRole.ADMINISTRATOR, UserRole.CONTENT_MANAGER])), db: AsyncSession = Depends(get_async_db)):
    row = await QuestionService.publish_question(db, question_id)
    return APIResponse(data=row, message="Approved question published")


@router.get("/manage/{question_id}/versions", response_model=APIResponse[List[ManagedQuestionResponse]])
async def question_versions(question_id: uuid.UUID, _auth=Depends(require_role([UserRole.ADMINISTRATOR, UserRole.CONTENT_MANAGER])), db: AsyncSession = Depends(get_async_db)):
    rows = await QuestionService.get_question_versions(db, question_id)
    return APIResponse(data=rows, message="Question revisions retrieved")


@router.post("/manage/{question_id}/restore/{version_id}", response_model=APIResponse[ManagedQuestionResponse])
async def restore_question_version(question_id: uuid.UUID, version_id: uuid.UUID,
    actor=Depends(require_role([UserRole.ADMINISTRATOR, UserRole.CONTENT_MANAGER])), db: AsyncSession = Depends(get_async_db)):
    row = await QuestionService.restore_question_version(db, question_id, version_id, actor.id)
    return APIResponse(data=row, message="Revision restored as a new pending version")


@router.patch("/manage/{question_id}", response_model=APIResponse[ManagedQuestionResponse])
async def update_question(question_id: uuid.UUID, request: QuestionUpdate,
    actor=Depends(require_role([UserRole.ADMINISTRATOR, UserRole.CONTENT_MANAGER])), db: AsyncSession = Depends(get_async_db)):
    row = await QuestionService.update_question(db, question_id, request, actor.id)
    return APIResponse(data=row, message="Question updated and returned to review")


@router.delete("/manage/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_question(question_id: uuid.UUID, _auth=Depends(require_role([UserRole.ADMINISTRATOR, UserRole.CONTENT_MANAGER])), db: AsyncSession = Depends(get_async_db)):
    await QuestionService.archive_question(db, question_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/history", response_model=APIResponse[List[PracticeHistoryItem]])
async def practice_history(page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100),
    candidate_profile: CandidateProfile = Depends(get_current_candidate_profile), db: AsyncSession = Depends(get_async_db)):
    rows, total = await QuestionService.get_practice_history(db, candidate_profile.id, page, limit)
    return APIResponse(data=rows, meta=PaginationMeta(page=page, limit=limit, total=total, total_pages=(total + limit - 1)//limit), message="Practice history retrieved")


@router.get("", response_model=APIResponse[List[CandidateQuestionResponse]])
async def list_questions(
    industry_id: Optional[uuid.UUID] = None, job_role_id: Optional[uuid.UUID] = None,
    industry_category_id: Optional[uuid.UUID] = None, skill_id: Optional[uuid.UUID] = None,
    subject_id: Optional[uuid.UUID] = None, topic_id: Optional[uuid.UUID] = None,
    experience_level_id: Optional[uuid.UUID] = None, company_id: Optional[uuid.UUID] = None,
    bookmarked: Optional[bool] = None, difficulty: Optional[DifficultyLevel] = None,
    question_type: Optional[QuestionType] = None, interview_round: Optional[str] = Query(None, max_length=100),
    search: Optional[str] = Query(None, max_length=200), page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    sort_by: Literal["created_at", "updated_at", "difficulty", "subject", "topic", "interview_round", "question_type"] = "created_at",
    sort_order: Literal["asc", "desc"] = "desc",
    candidate_profile: CandidateProfile = Depends(get_current_candidate_profile), db: AsyncSession = Depends(get_async_db),
):
    rows, total = await QuestionService.list_questions(db, candidate_profile_id=candidate_profile.id,
        industry_id=industry_id, job_role_id=job_role_id, difficulty=difficulty, question_type=question_type,
        interview_round=interview_round, industry_category_id=industry_category_id, skill_id=skill_id,
        subject_id=subject_id, topic_id=topic_id, experience_level_id=experience_level_id,
        company_id=company_id, bookmarked=bookmarked, search=search, page=page, limit=limit,
        sort_by=sort_by, sort_order=sort_order)
    return APIResponse(data=rows, meta=PaginationMeta(page=page, limit=limit, total=total, total_pages=(total + limit - 1)//limit), message="Questions retrieved")


@router.get("/{question_id}", response_model=APIResponse[CandidateQuestionResponse])
async def get_question(question_id: uuid.UUID, candidate_profile: CandidateProfile = Depends(get_current_candidate_profile), db: AsyncSession = Depends(get_async_db)):
    row = await QuestionService.get_question(db, question_id, candidate_profile.id)
    return APIResponse(data=row, message="Question retrieved")


@router.post("/{question_id}/bookmark", response_model=APIResponse[dict])
async def toggle_bookmark(question_id: uuid.UUID, candidate_profile: CandidateProfile = Depends(get_current_candidate_profile), db: AsyncSession = Depends(get_async_db)):
    value = await QuestionService.toggle_bookmark(db, question_id, candidate_profile.id)
    return APIResponse(data={"is_bookmarked": value}, message="Bookmark updated")


@router.post("/{question_id}/practice", response_model=APIResponse[QuestionPracticeResponse])
async def practice_question(question_id: uuid.UUID, request: QuestionPracticeRequest,
    candidate_profile: CandidateProfile = Depends(get_current_candidate_profile), db: AsyncSession = Depends(get_async_db)):
    result = await QuestionService.practice_question(db, question_id, candidate_profile.id, request)
    return APIResponse(data=result, message="Practice answer evaluated")


@router.post("", response_model=APIResponse[ManagedQuestionResponse], status_code=status.HTTP_201_CREATED)
async def create_question(request: QuestionCreate,
    actor=Depends(require_role([UserRole.ADMINISTRATOR, UserRole.CONTENT_MANAGER])), db: AsyncSession = Depends(get_async_db)):
    row = await QuestionService.create_question(db, request, actor.id)
    return APIResponse(data=row, message="Question created in pending review")
