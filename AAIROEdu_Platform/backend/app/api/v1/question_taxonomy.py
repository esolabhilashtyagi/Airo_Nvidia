import uuid
from typing import Literal, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_candidate_profile, require_role
from app.core.database import get_async_db
from app.models.candidate import CandidateProfile, Company
from app.models.taxonomy import ExperienceLevel, Industry, IndustryCategory, InterviewRound, JobRole, Skill, Subject, Topic
from app.models.user import UserRole
from app.schemas.common import APIResponse, PaginationMeta

router = APIRouter(prefix="/question-taxonomy", tags=["Question Taxonomy"])
TaxonomyKind = Literal["category", "job_role", "skill", "subject", "topic", "company", "experience_level", "interview_round"]
MODELS = {"category": IndustryCategory, "job_role": JobRole, "skill": Skill, "subject": Subject, "topic": Topic, "company": Company, "experience_level": ExperienceLevel, "interview_round": InterviewRound}


class TaxonomyWrite(BaseModel):
    kind: TaxonomyKind
    name: str = Field(min_length=2, max_length=255)
    industry_id: Optional[uuid.UUID] = None
    parent_id: Optional[uuid.UUID] = None
    description: Optional[str] = None
    category: Optional[str] = None
    is_technical: Optional[bool] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None


def as_dict(row):
    return {column.name: getattr(row, column.name) for column in row.__table__.columns}


@router.get("", response_model=APIResponse[dict])
async def list_candidate_taxonomy(industry_id: Optional[uuid.UUID] = None, subject_id: Optional[uuid.UUID] = None,
    profile: CandidateProfile = Depends(get_current_candidate_profile), db: AsyncSession = Depends(get_async_db)):
    industry_id = industry_id or profile.industry_id
    categories = await db.scalars(select(IndustryCategory).where(IndustryCategory.is_active.is_(True), IndustryCategory.industry_id == industry_id).order_by(IndustryCategory.name))
    roles = await db.scalars(select(JobRole).where(JobRole.is_active.is_(True), JobRole.industry_id == industry_id).order_by(JobRole.title))
    subjects = await db.scalars(select(Subject).where(Subject.is_active.is_(True), Subject.industry_id == industry_id).order_by(Subject.name))
    topic_query = select(Topic).join(Subject).where(Topic.is_active.is_(True), Subject.is_active.is_(True), Subject.industry_id == industry_id)
    if subject_id: topic_query = topic_query.where(Topic.subject_id == subject_id)
    topics = await db.scalars(topic_query.order_by(Topic.name))
    skills = await db.scalars(select(Skill).where(Skill.is_active.is_(True)).order_by(Skill.name))
    levels = await db.scalars(select(ExperienceLevel).where(ExperienceLevel.is_active.is_(True)).order_by(ExperienceLevel.name))
    rounds = await db.scalars(select(InterviewRound).where(InterviewRound.is_active.is_(True), InterviewRound.industry_id == industry_id).order_by(InterviewRound.name))
    industry = await db.get(Industry, industry_id) if industry_id else None
    company_query = select(Company).where(Company.is_active.is_(True))
    if industry: company_query = company_query.where(or_(Company.industry.is_(None), func.lower(Company.industry) == industry.name.lower()))
    companies = await db.scalars(company_query.order_by(Company.name))
    data = {"industry_id": industry_id, "categories": [as_dict(x) for x in categories.all()], "job_roles": [as_dict(x) for x in roles.all()],
        "subjects": [as_dict(x) for x in subjects.all()], "topics": [as_dict(x) for x in topics.all()], "skills": [as_dict(x) for x in skills.all()],
        "experience_levels": [as_dict(x) for x in levels.all()], "interview_rounds": [as_dict(x) for x in rounds.all()], "companies": [as_dict(x) for x in companies.all()]}
    return APIResponse(data=data, message="Question taxonomy retrieved")


@router.get("/manage/{kind}", response_model=APIResponse[list[dict]])
async def list_taxonomy(kind: TaxonomyKind, search: Optional[str] = Query(None, max_length=200), industry_id: Optional[uuid.UUID] = None,
    page: int = Query(1, ge=1), limit: int = Query(100, ge=1, le=500), _auth=Depends(require_role([UserRole.ADMINISTRATOR, UserRole.CONTENT_MANAGER])), db: AsyncSession = Depends(get_async_db)):
    model = MODELS[kind]
    name = getattr(model, "name", None)
    if name is None: name = getattr(model, "title")
    query = select(model)
    if search: query = query.where(name.ilike(f"%{search.strip()}%"))
    if industry_id and hasattr(model, "industry_id"): query = query.where(model.industry_id == industry_id)
    total = await db.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0
    rows = await db.scalars(query.order_by(name).offset((page-1)*limit).limit(limit))
    return APIResponse(data=[as_dict(row) for row in rows.all()], message="Taxonomy records retrieved",
        meta=PaginationMeta(page=page, limit=limit, total=total, total_pages=(total + limit - 1) // limit))


@router.post("/manage", response_model=APIResponse[dict], status_code=status.HTTP_201_CREATED)
async def create_taxonomy(request: TaxonomyWrite, _auth=Depends(require_role([UserRole.ADMINISTRATOR, UserRole.CONTENT_MANAGER])), db: AsyncSession = Depends(get_async_db)):
    kind=request.kind; industry=await db.get(Industry, request.industry_id) if request.industry_id else None
    if kind in {"category", "job_role", "subject", "interview_round"} and not request.industry_id: raise HTTPException(status_code=422, detail="An industry is required")
    if request.industry_id and (not industry or not industry.is_active): raise HTTPException(status_code=422, detail="An active industry is required")
    if kind == "category": row=IndustryCategory(industry_id=request.industry_id, name=request.name, description=request.description)
    elif kind == "job_role": row=JobRole(industry_id=request.industry_id, title=request.name, description=request.description, experience_level=request.category or "All Levels")
    elif kind == "skill": row=Skill(name=request.name, category=request.category, is_technical=request.is_technical if request.is_technical is not None else True)
    elif kind == "subject": row=Subject(industry_id=request.industry_id, name=request.name)
    elif kind == "topic":
        parent=await db.get(Subject, request.parent_id) if request.parent_id else None
        if not parent or not parent.is_active: raise HTTPException(status_code=422, detail="An active subject is required")
        row=Topic(subject_id=parent.id, name=request.name)
    elif kind == "company": row=Company(name=request.name, industry=industry.name if industry else None, website=request.website, logo_url=request.logo_url)
    elif kind == "experience_level": row=ExperienceLevel(name=request.name)
    else: row=InterviewRound(industry_id=request.industry_id, name=request.name)
    db.add(row); await db.commit(); await db.refresh(row)
    return APIResponse(data=as_dict(row), message="Taxonomy record created")


@router.patch("/manage/{kind}/{record_id}", response_model=APIResponse[dict])
async def update_taxonomy(kind: TaxonomyKind, record_id: uuid.UUID, request: TaxonomyWrite,
    _auth=Depends(require_role([UserRole.ADMINISTRATOR, UserRole.CONTENT_MANAGER])), db: AsyncSession = Depends(get_async_db)):
    if kind != request.kind: raise HTTPException(status_code=422, detail="Taxonomy kind does not match route")
    row=await db.get(MODELS[kind], record_id)
    if not row: raise HTTPException(status_code=404, detail="Taxonomy record not found")
    if kind == "job_role": row.title=request.name; row.description=request.description if request.description is not None else row.description
    else: row.name=request.name
    if kind in {"category", "job_role", "subject", "interview_round"} and request.industry_id:
        industry=await db.get(Industry, request.industry_id)
        if not industry or not industry.is_active: raise HTTPException(status_code=422, detail="An active industry is required")
        row.industry_id=request.industry_id
    if kind == "topic" and request.parent_id:
        parent=await db.get(Subject, request.parent_id)
        if not parent or not parent.is_active: raise HTTPException(status_code=422, detail="An active subject is required")
        row.subject_id=request.parent_id
    if kind == "skill":
        if request.category is not None: row.category=request.category
        if request.is_technical is not None: row.is_technical=request.is_technical
    if kind == "company":
        if request.website is not None: row.website=request.website
        if request.logo_url is not None: row.logo_url=request.logo_url
        if request.industry_id: row.industry=industry.name
    if kind == "category" and request.description is not None:
        row.description = request.description
    if kind == "job_role" and request.category is not None:
        row.experience_level = request.category
    if kind == "subject" and request.industry_id is None:
        raise HTTPException(status_code=422, detail="An industry is required")
    if kind in {"category", "job_role", "subject", "interview_round"} and request.industry_id is None:
        raise HTTPException(status_code=422, detail="An industry is required")
    await db.commit(); await db.refresh(row)
    return APIResponse(data=as_dict(row), message="Taxonomy record updated")


@router.delete("/manage/{kind}/{record_id}", response_model=APIResponse[dict])
async def deactivate_taxonomy(kind: TaxonomyKind, record_id: uuid.UUID, _auth=Depends(require_role([UserRole.ADMINISTRATOR])), db: AsyncSession = Depends(get_async_db)):
    row=await db.get(MODELS[kind], record_id)
    if not row: raise HTTPException(status_code=404, detail="Taxonomy record not found")
    row.is_active=False
    await db.commit()
    return APIResponse(data={"id": row.id, "is_active": False}, message="Taxonomy deactivated; historical links remain")


@router.patch("/manage/{kind}/{record_id}/active", response_model=APIResponse[dict])
async def set_taxonomy_active(kind: TaxonomyKind, record_id: uuid.UUID, active: bool = Query(...),
    _auth=Depends(require_role([UserRole.ADMINISTRATOR])), db: AsyncSession = Depends(get_async_db)):
    row = await db.get(MODELS[kind], record_id)
    if not row:
        raise HTTPException(status_code=404, detail="Taxonomy record not found")
    row.is_active = active
    await db.commit()
    return APIResponse(data={"id": row.id, "is_active": row.is_active}, message=f"Taxonomy {'reactivated' if active else 'deactivated'}")
