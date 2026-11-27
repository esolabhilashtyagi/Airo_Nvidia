"""
API Router for Company Interview Intelligence in AAIROEdu_Platform.
Exposes endpoints for authentic company questions, 5-round hiring blueprints, and candidate practice.
"""

from typing import Any, List, Optional, Union
from fastapi import APIRouter, Depends, Query, Security, status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, security_bearer
from app.core.database import get_async_db
from app.models.candidate import CandidateProfile
from app.schemas.common import APIResponse, PaginationMeta
from app.services.interview_intelligence_bridge import (
    CompanyBlueprintDTO,
    CompanyInterviewQuestionDTO,
    CompanySummaryDTO,
    DynamicDorksDTO,
    InterviewIntelligenceBridge,
    SynthesizedRoundQuestionDTO,
)

router = APIRouter(prefix="/questions/company-intel", tags=["Company Interview Intelligence"])


async def get_optional_candidate_profile(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    db: AsyncSession = Depends(get_async_db),
) -> Optional[CandidateProfile]:
    if not credentials:
        return None
    try:
        user = await get_current_user(credentials=credentials, db=db)
        return getattr(user, "candidate_profile", None)
    except Exception:
        return None


class PracticeAnswerRequest(BaseModel):
    question_id: str
    user_response: str = Field(min_length=3, max_length=15000)


class GenerateDorksRequest(BaseModel):
    company: str = "Google"
    role: str = "Software Development Engineer"
    yoe: Union[float, str] = 3.5
    skills: List[str] = Field(default_factory=list)

    @field_validator("yoe", mode="before")
    @classmethod
    def parse_yoe(cls, v: Any) -> float:
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            import re
            m = re.search(r"\d+(\.\d+)?", v)
            if m:
                return float(m.group(0))
        return 3.5


class RoundQuestionsRequest(BaseModel):
    company: str = "Google"
    role: str = "Software Development Engineer"
    yoe: Union[float, str] = 3.5
    round_number: Optional[int] = None
    skills: List[str] = Field(default_factory=list)

    @field_validator("yoe", mode="before")
    @classmethod
    def parse_yoe(cls, v: Any) -> float:
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            import re
            m = re.search(r"\d+(\.\d+)?", v)
            if m:
                return float(m.group(0))
        return 3.5


class LiveScrapeRequest(BaseModel):
    company: str = "Google"
    industry: Optional[str] = None
    role: str = "Software Engineer"
    yoe: Optional[float] = 3.5
    skills: Optional[List[str]] = Field(default_factory=list)
    round_number: Optional[int] = None
    difficulty: Optional[str] = None
    platforms: Optional[List[str]] = Field(default_factory=list)
    keyword: Optional[str] = ""
    limit: Optional[int] = 30
    max_pages: int = 3


@router.get("", response_model=APIResponse[List[CompanyInterviewQuestionDTO]])
async def list_company_questions(
    company: Optional[str] = Query(None, description="Filter by company name (e.g. Google, Meta, Amazon)"),
    role: Optional[str] = Query(None, description="Filter by job role"),
    category: Optional[str] = Query(None, description="Filter by category (DSA, System Design, etc.)"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty (Easy, Medium, Hard)"),
    round_number: Optional[int] = Query(None, ge=1, le=5, description="Filter by canonical round (1 to 5)"),
    search: Optional[str] = Query(None, max_length=200, description="Keyword search in question text or company"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    _candidate: Optional[CandidateProfile] = Depends(get_optional_candidate_profile),
):
    """Retrieve authentic, verified company interview questions with multi-faceted filtering."""
    questions, total = InterviewIntelligenceBridge.list_questions(
        company=company,
        role=role,
        category=category,
        difficulty=difficulty,
        round_number=round_number,
        search=search,
        page=page,
        limit=limit,
    )
    total_pages = (total + limit - 1) // limit if limit > 0 else 1
    return APIResponse(
        data=questions,
        meta=PaginationMeta(page=page, limit=limit, total=total, total_pages=total_pages),
        message="Authentic company interview questions retrieved successfully",
    )


@router.get("/companies", response_model=APIResponse[List[CompanySummaryDTO]])
async def list_companies(
    _candidate: Optional[CandidateProfile] = Depends(get_optional_candidate_profile),
):
    """List indexed tech companies with question counts and round coverage."""
    companies = InterviewIntelligenceBridge.list_companies()
    return APIResponse(
        data=companies,
        message="Company interview intelligence directory retrieved",
    )


@router.get("/roles", response_model=APIResponse[List[str]])
async def list_roles(
    company: Optional[str] = Query(None, description="Optional company filter"),
    _candidate: Optional[CandidateProfile] = Depends(get_optional_candidate_profile),
):
    """List distinct indexed job roles across companies."""
    roles = InterviewIntelligenceBridge.list_roles(company=company)
    return APIResponse(
        data=roles,
        message="Job roles directory retrieved",
    )


@router.get("/categories", response_model=APIResponse[List[str]])
async def list_categories(
    company: Optional[str] = Query(None, description="Optional company filter"),
    _candidate: Optional[CandidateProfile] = Depends(get_optional_candidate_profile),
):
    """List distinct question categories across companies."""
    categories = InterviewIntelligenceBridge.list_categories(company=company)
    return APIResponse(
        data=categories,
        message="Question categories directory retrieved",
    )


@router.get("/blueprint/{company_name}", response_model=APIResponse[CompanyBlueprintDTO])
async def get_company_blueprint(
    company_name: str,
    role: str = Query("Software Development Engineer", description="Target role"),
    yoe: float = Query(3.5, ge=0.0, le=30.0, description="Years of experience"),
    _candidate: Optional[CandidateProfile] = Depends(get_optional_candidate_profile),
):
    """Retrieve full 5-round hiring blueprint for target company."""
    blueprint = InterviewIntelligenceBridge.get_company_blueprint(
        company_name=company_name,
        role=role,
        yoe=yoe,
    )
    return APIResponse(
        data=blueprint,
        message=f"Hiring blueprint for {company_name} generated successfully",
    )


@router.post("/generate-dorks", response_model=APIResponse[DynamicDorksDTO])
async def generate_company_dorks(
    payload: GenerateDorksRequest,
    _candidate: Optional[CandidateProfile] = Depends(get_optional_candidate_profile),
):
    """Generate dynamic round-by-round open web search dorks with Nemotron."""
    dorks = await InterviewIntelligenceBridge.generate_dynamic_dorks(
        company=payload.company,
        role=payload.role,
        yoe=payload.yoe,
        skills=payload.skills,
    )
    return APIResponse(
        data=dorks,
        message=f"Dynamic domain dorks generated for {payload.company}",
    )


@router.get("/generate-dorks", response_model=APIResponse[DynamicDorksDTO])
async def generate_company_dorks_get(
    company: str = Query("Google"),
    role: str = Query("Software Development Engineer"),
    yoe: float = Query(3.5, ge=0.0, le=30.0),
    skills: Optional[str] = Query(None),
    _candidate: Optional[CandidateProfile] = Depends(get_optional_candidate_profile),
):
    """GET query variant for dynamic domain dorks."""
    skills_list = [s.strip() for s in skills.split(",")] if skills else []
    dorks = await InterviewIntelligenceBridge.generate_dynamic_dorks(
        company=company,
        role=role,
        yoe=yoe,
        skills=skills_list,
    )
    return APIResponse(
        data=dorks,
        message=f"Dynamic domain dorks generated for {company}",
    )


@router.post("/round-questions", response_model=APIResponse[List[SynthesizedRoundQuestionDTO]])
async def synthesize_round_questions(
    payload: RoundQuestionsRequest,
    _candidate: Optional[CandidateProfile] = Depends(get_optional_candidate_profile),
):
    """Synthesize verified questions tailored for canonical rounds 1-5."""
    questions = await InterviewIntelligenceBridge.synthesize_round_questions(
        company=payload.company,
        role=payload.role,
        yoe=payload.yoe,
        skills=payload.skills,
        round_number=payload.round_number,
    )
    return APIResponse(
        data=questions,
        message=f"Verified round questions synthesized for {payload.company}",
    )


@router.get("/round-questions", response_model=APIResponse[List[SynthesizedRoundQuestionDTO]])
async def synthesize_round_questions_get(
    company: str = Query("Google"),
    role: str = Query("Software Development Engineer"),
    yoe: float = Query(3.5, ge=0.0, le=30.0),
    round_number: Optional[int] = Query(None, ge=1, le=5),
    skills: Optional[str] = Query(None),
    _candidate: Optional[CandidateProfile] = Depends(get_optional_candidate_profile),
):
    """GET query variant for verified round questions."""
    skills_list = [s.strip() for s in skills.split(",")] if skills else []
    questions = await InterviewIntelligenceBridge.synthesize_round_questions(
        company=company,
        role=role,
        yoe=yoe,
        skills=skills_list,
        round_number=round_number,
    )
    return APIResponse(
        data=questions,
        message=f"Verified round questions synthesized for {company}",
    )


@router.post("/live-scrape", response_model=APIResponse[dict])
async def trigger_live_scrape(
    payload: LiveScrapeRequest,
    _candidate: Optional[CandidateProfile] = Depends(get_optional_candidate_profile),
):
    """Trigger live web extraction and store verified questions."""
    result = await InterviewIntelligenceBridge.trigger_live_scrape(
        company=payload.company,
        industry=payload.industry,
        role=payload.role,
        yoe=payload.yoe if payload.yoe is not None else 3.5,
        skills=payload.skills or [],
        round_number=payload.round_number,
        difficulty=payload.difficulty,
        platforms=payload.platforms or [],
        keyword=payload.keyword or "",
        limit=payload.limit or 30,
        max_pages=payload.max_pages,
    )
    return APIResponse(
        data=result,
        message=f"Live scraping completed for {payload.company}",
    )


@router.get("/{question_id}", response_model=APIResponse[CompanyInterviewQuestionDTO])
async def get_company_question(
    question_id: str,
    _candidate: Optional[CandidateProfile] = Depends(get_optional_candidate_profile),
):
    """Retrieve specific verified company question details."""
    q = InterviewIntelligenceBridge.get_question_by_id(question_id)
    if not q:
        return APIResponse(
            data=None,
            success=False,
            message="Question not found",
        )
    return APIResponse(
        data=q,
        message="Company question details retrieved",
    )


@router.post("/practice", response_model=APIResponse[dict])
async def practice_company_question(
    payload: PracticeAnswerRequest,
    _candidate: Optional[CandidateProfile] = Depends(get_optional_candidate_profile),
):
    """Evaluate candidate practice response against authentic company interview standards."""
    result = await InterviewIntelligenceBridge.evaluate_practice_answer(
        question_id=payload.question_id,
        user_response=payload.user_response,
    )
    return APIResponse(
        data=result,
        message="Practice answer evaluated against company standards",
    )
