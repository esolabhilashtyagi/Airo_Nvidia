import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_candidate_profile, require_role
from app.core.database import get_async_db
from app.models.candidate import CandidateProfile
from app.models.module import Lesson, Module
from app.models.taxonomy import Industry, JobRole, Skill
from app.models.user import UserRole
from app.schemas.common import APIResponse
from app.schemas.module import (LessonManageCreate, LessonResponse, ModuleManageCreate,
    ModuleManageUpdate, ModuleResponse, RoadmapResponse, RoadmapTaskResponse)
from app.services.module_service import ModuleService

router = APIRouter(prefix="/modules", tags=["Learning Modules & Roadmaps"])


@router.get("/manage", response_model=APIResponse[List[ModuleResponse]])
async def manage_modules(_auth=Depends(require_role([UserRole.ADMINISTRATOR, UserRole.CONTENT_MANAGER])), db: AsyncSession = Depends(get_async_db)):
    rows = await db.scalars(select(Module).options(selectinload(Module.lessons), selectinload(Module.job_roles), selectinload(Module.skills)).order_by(Module.updated_at.desc()).limit(200))
    return APIResponse(data=[ModuleResponse.model_validate(row) for row in rows.all()], message="Module content retrieved")


@router.post("/manage", response_model=APIResponse[ModuleResponse], status_code=status.HTTP_201_CREATED)
async def create_module(request: ModuleManageCreate, _auth=Depends(require_role([UserRole.ADMINISTRATOR, UserRole.CONTENT_MANAGER])), db: AsyncSession = Depends(get_async_db)):
    industry = await db.get(Industry, request.industry_id)
    if not industry or not industry.is_active:
        raise HTTPException(status_code=422, detail="An active industry is required")
    roles = list((await db.scalars(select(JobRole).where(JobRole.id.in_(request.job_role_ids)))).all()) if request.job_role_ids else []
    skills = list((await db.scalars(select(Skill).where(Skill.id.in_(request.skill_ids)))).all()) if request.skill_ids else []
    if len(roles) != len(request.job_role_ids) or any(not role.is_active or role.industry_id != industry.id for role in roles):
        raise HTTPException(status_code=422, detail="Every job role must be active and belong to the selected industry")
    if len(skills) != len(request.skill_ids) or any(not skill.is_active for skill in skills):
        raise HTTPException(status_code=422, detail="Every skill must be active")
    module = Module(**request.model_dump(exclude={"job_role_ids", "skill_ids"}), job_roles=roles, skills=skills)
    if module.is_published:
        raise HTTPException(status_code=422, detail="Create modules as drafts and add a lesson before publishing")
    db.add(module)
    await db.commit()
    loaded = await db.scalar(select(Module).where(Module.id == module.id).options(selectinload(Module.lessons), selectinload(Module.job_roles), selectinload(Module.skills)))
    return APIResponse(data=ModuleResponse.model_validate(loaded), message="Module draft created")


@router.patch("/manage/{module_id}", response_model=APIResponse[ModuleResponse])
async def update_module(module_id: uuid.UUID, request: ModuleManageUpdate, _auth=Depends(require_role([UserRole.ADMINISTRATOR, UserRole.CONTENT_MANAGER])), db: AsyncSession = Depends(get_async_db)):
    module = await db.scalar(select(Module).where(Module.id == module_id).options(selectinload(Module.lessons), selectinload(Module.job_roles), selectinload(Module.skills)).with_for_update())
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    changes = request.model_dump(exclude_unset=True)
    role_ids = changes.pop("job_role_ids", None)
    skill_ids = changes.pop("skill_ids", None)
    if role_ids is not None:
        roles = list((await db.scalars(select(JobRole).where(JobRole.id.in_(role_ids)))).all()) if role_ids else []
        if len(roles) != len(role_ids) or any(not role.is_active or role.industry_id != module.industry_id for role in roles):
            raise HTTPException(status_code=422, detail="Every job role must be active and belong to the module industry")
        module.job_roles = roles
    if skill_ids is not None:
        skills = list((await db.scalars(select(Skill).where(Skill.id.in_(skill_ids)))).all()) if skill_ids else []
        if len(skills) != len(skill_ids) or any(not skill.is_active for skill in skills):
            raise HTTPException(status_code=422, detail="Every skill must be active")
        module.skills = skills
    active_lessons = [lesson for lesson in module.lessons if not lesson.is_archived]
    if changes.get("is_published") is True and not active_lessons:
        raise HTTPException(status_code=422, detail="A module needs at least one lesson before publishing")
    for key, value in changes.items():
        setattr(module, key, value)
    await db.commit()
    loaded = await db.scalar(select(Module).where(Module.id == module.id).options(selectinload(Module.lessons), selectinload(Module.job_roles), selectinload(Module.skills)))
    return APIResponse(data=ModuleResponse.model_validate(loaded), message="Module updated")


@router.post("/manage/{module_id}/lessons", response_model=APIResponse[LessonResponse], status_code=status.HTTP_201_CREATED)
async def create_lesson(module_id: uuid.UUID, request: LessonManageCreate, _auth=Depends(require_role([UserRole.ADMINISTRATOR, UserRole.CONTENT_MANAGER])), db: AsyncSession = Depends(get_async_db)):
    module = await db.scalar(select(Module).where(Module.id == module_id).with_for_update())
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    module.is_published = False
    lesson = Lesson(module_id=module.id, **request.model_dump())
    db.add(lesson)
    await db.commit()
    await db.refresh(lesson)
    return APIResponse(data=LessonResponse.model_validate(lesson), message="Lesson added; the module returned to draft review")


@router.patch("/manage/{module_id}/lessons/{lesson_id}", response_model=APIResponse[LessonResponse])
async def update_lesson(module_id: uuid.UUID, lesson_id: uuid.UUID, request: LessonManageCreate,
    _auth=Depends(require_role([UserRole.ADMINISTRATOR, UserRole.CONTENT_MANAGER])), db: AsyncSession = Depends(get_async_db)):
    lesson = await db.scalar(select(Lesson).where(Lesson.id == lesson_id, Lesson.module_id == module_id).with_for_update())
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    for key, value in request.model_dump().items():
        setattr(lesson, key, value)
    module = await db.get(Module, module_id)
    module.is_published = False
    await db.commit()
    await db.refresh(lesson)
    return APIResponse(data=LessonResponse.model_validate(lesson), message="Lesson updated; module returned to draft review")


@router.delete("/manage/{module_id}/lessons/{lesson_id}", response_model=APIResponse[dict])
async def archive_lesson(module_id: uuid.UUID, lesson_id: uuid.UUID,
    _auth=Depends(require_role([UserRole.ADMINISTRATOR, UserRole.CONTENT_MANAGER])), db: AsyncSession = Depends(get_async_db)):
    lesson = await db.scalar(select(Lesson).where(Lesson.id == lesson_id, Lesson.module_id == module_id).with_for_update())
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    lesson.is_archived = True
    module = await db.get(Module, module_id)
    module.is_published = False
    await db.commit()
    return APIResponse(data={"id": lesson.id, "is_archived": True}, message="Lesson archived; progress history retained")


@router.delete("/manage/{module_id}", response_model=APIResponse[dict])
async def archive_module(module_id: uuid.UUID, _auth=Depends(require_role([UserRole.ADMINISTRATOR])), db: AsyncSession = Depends(get_async_db)):
    module = await db.get(Module, module_id)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    module.is_archived = True
    module.is_published = False
    await db.commit()
    return APIResponse(data={"id": module.id, "is_archived": True}, message="Module archived; candidate progress retained")


@router.get("", response_model=APIResponse[List[ModuleResponse]])
async def list_modules(
    candidate_profile: CandidateProfile = Depends(get_current_candidate_profile),
    db: AsyncSession = Depends(get_async_db)
):
    modules = await ModuleService.list_modules_for_candidate(db, candidate_profile)
    return APIResponse(data=modules, message="Modules retrieved")


@router.get("/roadmap/active", response_model=APIResponse[Optional[RoadmapResponse]])
async def get_active_roadmap(
    candidate_profile: CandidateProfile = Depends(get_current_candidate_profile),
    db: AsyncSession = Depends(get_async_db)
):
    roadmap = await ModuleService.get_candidate_roadmap(db, candidate_profile.id)
    return APIResponse(data=roadmap, message="Candidate roadmap retrieved")


@router.post("/roadmap/tasks/{task_id}/toggle", response_model=APIResponse[RoadmapTaskResponse])
async def toggle_roadmap_task(
    task_id: uuid.UUID,
    candidate_profile: CandidateProfile = Depends(get_current_candidate_profile),
    db: AsyncSession = Depends(get_async_db)
):
    task = await ModuleService.toggle_roadmap_task(db, task_id, candidate_profile.id)
    return APIResponse(data=task, message="Roadmap task updated")


@router.get("/{module_id}", response_model=APIResponse[ModuleResponse])
async def get_module_detail(
    module_id: uuid.UUID,
    candidate_profile: CandidateProfile = Depends(get_current_candidate_profile),
    db: AsyncSession = Depends(get_async_db)
):
    module = await ModuleService.get_module_detail(db, module_id, candidate_profile)
    return APIResponse(data=module, message="Module details retrieved")


@router.post("/{module_id}/enroll", response_model=APIResponse[ModuleResponse])
async def enroll_module(
    module_id: uuid.UUID,
    candidate_profile: CandidateProfile = Depends(get_current_candidate_profile),
    db: AsyncSession = Depends(get_async_db),
):
    module = await ModuleService.enroll_module(db, module_id, candidate_profile)
    return APIResponse(data=module, message="Module enrollment saved")


@router.post("/{module_id}/lessons/{lesson_id}/complete", response_model=APIResponse[ModuleResponse])
async def complete_lesson(
    module_id: uuid.UUID,
    lesson_id: uuid.UUID,
    candidate_profile: CandidateProfile = Depends(get_current_candidate_profile),
    db: AsyncSession = Depends(get_async_db)
):
    updated_mod = await ModuleService.complete_lesson(db, module_id, lesson_id, candidate_profile)
    return APIResponse(data=updated_mod, message="Lesson marked as completed")


