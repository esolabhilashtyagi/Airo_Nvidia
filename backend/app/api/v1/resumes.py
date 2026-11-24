import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.concurrency import run_in_threadpool

from app.api.deps import get_current_candidate_profile
from app.core.database import get_async_db
from app.core.config import settings
from app.models.candidate import CandidateProfile
from app.schemas.common import APIResponse
from app.schemas.resume import (
    ResumeAnalysisResponse,
    ResumeATSReviewRequest,
    ResumeATSReviewResponse,
    ResumeDetailResponse,
    ResumeParsedDataUpdate,
    ResumeResponse,
    ResumeSuggestionResponse,
    ResumeVersionResponse,
    SuggestionActionRequest,
)
from app.services.resume_service import ResumeService
from app.services.resume_builder import build_profile_resume_docx, build_profile_resume_pdf, safe_resume_filename

router = APIRouter(prefix="/resumes", tags=["Resume Intelligence"])


@router.post("/upload", response_model=APIResponse[ResumeResponse], status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile = File(...),
    candidate_profile: CandidateProfile = Depends(get_current_candidate_profile),
    db: AsyncSession = Depends(get_async_db),
):
    await ResumeService.enforce_rate_limit(db, candidate_profile.id, "upload")
    resume = await ResumeService.upload_resume(db, candidate_profile, file)
    message = "Resume uploaded and text extracted." if resume.parsing_status == "extracted" else "Resume uploaded; text extraction needs attention."
    return APIResponse(data=resume, message=message)


@router.post("/job-description/extract", response_model=APIResponse[str])
async def extract_job_description(
    file: UploadFile = File(...),
    _candidate_profile: CandidateProfile = Depends(get_current_candidate_profile),
):
    content = await file.read(settings.MAX_UPLOAD_SIZE_BYTES + 1)
    if len(content) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=413, detail=f"File exceeds the {settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)} MB upload limit.")
    text = await run_in_threadpool(ResumeService.extract_job_description, file.filename or "", file.content_type, content)
    return APIResponse(data=text, message="Job description text extracted; source file was not stored.")


@router.get("", response_model=APIResponse[List[ResumeResponse]])
async def list_resumes(
    candidate_profile: CandidateProfile = Depends(get_current_candidate_profile),
    db: AsyncSession = Depends(get_async_db),
):
    resumes = await ResumeService.list_resumes(db, candidate_profile.id)
    return APIResponse(data=resumes, message="Resumes retrieved")


@router.post("/generate-from-profile", response_class=StreamingResponse)
async def generate_resume_from_profile(
    template: str = Query(default="modern", pattern="^(modern|classic|compact)$"),
    file_format: str = Query(default="pdf", alias="format", pattern="^(pdf|docx)$"),
    candidate_profile: CandidateProfile = Depends(get_current_candidate_profile),
    db: AsyncSession = Depends(get_async_db),
):
    """Download a PDF or editable DOCX assembled solely from the candidate's saved profile."""
    result = await db.execute(
        select(CandidateProfile)
        .where(CandidateProfile.id == candidate_profile.id)
        .options(
            selectinload(CandidateProfile.user),
            selectinload(CandidateProfile.education_history),
            selectinload(CandidateProfile.experience_history),
        )
    )
    profile = result.scalar_one_or_none()
    if not profile or not profile.user:
        raise HTTPException(status_code=404, detail="Candidate profile was not found.")
    try:
        builder = build_profile_resume_pdf if file_format == "pdf" else build_profile_resume_docx
        content = await run_in_threadpool(builder, profile.user, profile, template)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    filename = safe_resume_filename(profile.user.full_name, template, file_format)
    media_type = "application/pdf" if file_format == "pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return StreamingResponse(
        iter([content]),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{resume_id}", response_model=APIResponse[ResumeDetailResponse])
async def get_resume(
    resume_id: uuid.UUID,
    candidate_profile: CandidateProfile = Depends(get_current_candidate_profile),
    db: AsyncSession = Depends(get_async_db),
):
    resume = await ResumeService.get_resume(db, resume_id, candidate_profile.id)
    return APIResponse(data=resume, message="Resume details retrieved")


@router.post("/{resume_id}/extract", response_model=APIResponse[ResumeDetailResponse])
async def extract_resume(
    resume_id: uuid.UUID,
    candidate_profile: CandidateProfile = Depends(get_current_candidate_profile),
    db: AsyncSession = Depends(get_async_db),
):
    await ResumeService.enforce_rate_limit(db, candidate_profile.id, "extract")
    resume = await ResumeService.extract_resume(db, resume_id, candidate_profile.id)
    return APIResponse(data=resume, message="Resume extraction completed")


@router.put("/{resume_id}/parsed-data", response_model=APIResponse[ResumeDetailResponse])
async def update_parsed_data(
    resume_id: uuid.UUID,
    request: ResumeParsedDataUpdate,
    candidate_profile: CandidateProfile = Depends(get_current_candidate_profile),
    db: AsyncSession = Depends(get_async_db),
):
    resume = await ResumeService.update_parsed_data(db, resume_id, candidate_profile.id, request)
    return APIResponse(data=resume, message="Corrected resume information saved as a new version")


@router.get("/{resume_id}/versions", response_model=APIResponse[List[ResumeVersionResponse]])
async def list_resume_versions(
    resume_id: uuid.UUID,
    candidate_profile: CandidateProfile = Depends(get_current_candidate_profile),
    db: AsyncSession = Depends(get_async_db),
):
    versions = await ResumeService.list_versions(db, resume_id, candidate_profile.id)
    return APIResponse(data=versions, message="Resume versions retrieved")


@router.get("/{resume_id}/analysis", response_model=APIResponse[Optional[ResumeAnalysisResponse]])
async def get_resume_analysis(
    resume_id: uuid.UUID,
    candidate_profile: CandidateProfile = Depends(get_current_candidate_profile),
    db: AsyncSession = Depends(get_async_db),
):
    analysis = await ResumeService.get_analysis(db, resume_id, candidate_profile.id)
    return APIResponse(data=analysis, message="Resume analysis retrieved")


@router.post("/{resume_id}/ats-review", response_model=APIResponse[ResumeATSReviewResponse], status_code=status.HTTP_201_CREATED)
async def create_ats_review(
    resume_id: uuid.UUID,
    request: ResumeATSReviewRequest,
    candidate_profile: CandidateProfile = Depends(get_current_candidate_profile),
    db: AsyncSession = Depends(get_async_db),
):
    review = await ResumeService.create_ats_review(db, resume_id, candidate_profile.id, request)
    return APIResponse(data=review, message="Job-specific resume match estimate saved")


@router.get("/{resume_id}/ats-review", response_model=APIResponse[Optional[ResumeATSReviewResponse]])
async def get_ats_review(
    resume_id: uuid.UUID,
    candidate_profile: CandidateProfile = Depends(get_current_candidate_profile),
    db: AsyncSession = Depends(get_async_db),
):
    review = await ResumeService.get_latest_ats_review(db, resume_id, candidate_profile.id)
    return APIResponse(data=review, message="Latest job-specific resume match estimate retrieved")


@router.post("/{resume_id}/analyze", response_model=APIResponse[ResumeAnalysisResponse])
@router.post("/{resume_id}/enhance", response_model=APIResponse[ResumeAnalysisResponse])
async def analyze_resume(
    resume_id: uuid.UUID,
    request: Optional[ResumeATSReviewRequest] = None,
    candidate_profile: CandidateProfile = Depends(get_current_candidate_profile),
    db: AsyncSession = Depends(get_async_db),
):
    await ResumeService.enforce_rate_limit(db, candidate_profile.id, "ai")
    analysis = await ResumeService.analyze_resume(db, resume_id, candidate_profile, request)
    return APIResponse(data=analysis, message="Role-aware resume analysis completed")


@router.post("/suggestions/{suggestion_id}/action", response_model=APIResponse[ResumeSuggestionResponse])
async def handle_suggestion_action(
    suggestion_id: uuid.UUID,
    request: SuggestionActionRequest,
    candidate_profile: CandidateProfile = Depends(get_current_candidate_profile),
    db: AsyncSession = Depends(get_async_db),
):
    updated = await ResumeService.handle_suggestion_action(
        db, suggestion_id, candidate_profile.id, request.action, request.edited_text
    )
    return APIResponse(data=updated, message=f"Suggestion {request.action}ed successfully")


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resume(
    resume_id: uuid.UUID,
    candidate_profile: CandidateProfile = Depends(get_current_candidate_profile),
    db: AsyncSession = Depends(get_async_db),
):
    await ResumeService.delete_resume(db, resume_id, candidate_profile.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
