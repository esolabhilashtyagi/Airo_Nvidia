import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.candidate import CandidateProfile
from app.models.module import CandidateModuleProgress, Lesson, LessonProgress, Module, ModuleProgressStatus, Roadmap, RoadmapTask
from app.schemas.module import LessonResponse, ModuleResponse, RoadmapResponse, RoadmapTaskResponse


class ModuleService:
    @staticmethod
    async def enroll_module(db: AsyncSession, module_id: uuid.UUID, candidate_profile: CandidateProfile) -> ModuleResponse:
        module_query = select(Module).where(Module.id == module_id, Module.is_published.is_(True))
        if candidate_profile.industry_id:
            module_query = module_query.where(Module.industry_id == candidate_profile.industry_id)
        module = await db.scalar(module_query)
        if not module:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learning module not found")
        progress = await db.scalar(select(CandidateModuleProgress).where(
            CandidateModuleProgress.candidate_profile_id == candidate_profile.id,
            CandidateModuleProgress.module_id == module_id,
        ))
        if not progress:
            progress = CandidateModuleProgress(
                candidate_profile_id=candidate_profile.id,
                module_id=module_id,
                status=ModuleProgressStatus.IN_PROGRESS,
                completion_percentage=0,
                last_accessed_at=datetime.now(timezone.utc),
            )
            db.add(progress)
        else:
            progress.last_accessed_at = datetime.now(timezone.utc)
        await db.commit()
        return await ModuleService.get_module_detail(db, module_id, candidate_profile)

    @staticmethod
    async def list_modules_for_candidate(
        db: AsyncSession,
        candidate_profile: CandidateProfile
    ) -> List[ModuleResponse]:
        query = (
            select(Module)
            .where(Module.is_published.is_(True), Module.is_archived.is_(False))
            .options(selectinload(Module.lessons.and_(Lesson.is_archived.is_(False))), selectinload(Module.job_roles), selectinload(Module.skills))
            .order_by(Module.order_index.asc())
        )
        if candidate_profile.industry_id:
            query = query.where(Module.industry_id == candidate_profile.industry_id)

        result = await db.execute(query)
        modules = result.scalars().all()
        candidate_roles = {str(value).strip().casefold() for value in (candidate_profile.current_role, candidate_profile.target_role) if value}
        candidate_skills = {str(value).strip().casefold() for value in (candidate_profile.key_skills or []) if value}
        modules = [module for module in modules if
            (not module.job_roles or any(role.title.strip().casefold() in candidate_roles for role in module.job_roles)) and
            (not module.skills or any(skill.name.strip().casefold() in candidate_skills for skill in module.skills))]

        # Load candidate progress
        prog_query = select(CandidateModuleProgress).where(
            CandidateModuleProgress.candidate_profile_id == candidate_profile.id
        )
        prog_res = await db.execute(prog_query)
        progress_map = {p.module_id: p for p in prog_res.scalars().all()}
        lesson_ids = [lesson.id for module in modules for lesson in module.lessons]
        completed_ids = set()
        if lesson_ids:
            completed_res = await db.execute(select(LessonProgress.lesson_id).where(
                LessonProgress.candidate_profile_id == candidate_profile.id,
                LessonProgress.lesson_id.in_(lesson_ids),
            ))
            completed_ids = set(completed_res.scalars().all())

        output: List[ModuleResponse] = []
        for m in modules:
            resp = ModuleResponse.model_validate(m)
            if m.id in progress_map:
                p_record = progress_map[m.id]
                resp.progress_status = p_record.status
                resp.completion_percentage = p_record.completion_percentage
            resp.completed_lesson_ids = [lesson.id for lesson in m.lessons if lesson.id in completed_ids]
            output.append(resp)

        return output

    @staticmethod
    async def get_module_detail(
        db: AsyncSession,
        module_id: uuid.UUID,
        candidate_profile: CandidateProfile
    ) -> ModuleResponse:
        query = (
            select(Module)
            .where(Module.id == module_id, Module.is_published.is_(True), Module.is_archived.is_(False))
            .options(selectinload(Module.lessons.and_(Lesson.is_archived.is_(False))), selectinload(Module.job_roles), selectinload(Module.skills))
        )
        if candidate_profile.industry_id:
            query = query.where(Module.industry_id == candidate_profile.industry_id)
        result = await db.execute(query)
        m = result.scalar_one_or_none()
        if not m:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Learning module not found"
            )

        resp = ModuleResponse.model_validate(m)

        # Check candidate progress
        p_q = select(CandidateModuleProgress).where(
            CandidateModuleProgress.candidate_profile_id == candidate_profile.id,
            CandidateModuleProgress.module_id == module_id
        )
        p_res = await db.execute(p_q)
        prog = p_res.scalar_one_or_none()
        if prog:
            resp.progress_status = prog.status
            resp.completion_percentage = prog.completion_percentage
        completed_res = await db.execute(select(LessonProgress.lesson_id).join(Lesson, Lesson.id == LessonProgress.lesson_id).where(
            LessonProgress.candidate_profile_id == candidate_profile.id,
            Lesson.module_id == module_id,
        ))
        resp.completed_lesson_ids = list(completed_res.scalars().all())

        return resp

    @staticmethod
    async def complete_lesson(
        db: AsyncSession,
        module_id: uuid.UUID,
        lesson_id: uuid.UUID,
        candidate_profile: CandidateProfile
    ) -> ModuleResponse:
        # Check module and lesson existence
        mod = await db.get(Module, module_id)
        lesson = await db.get(Lesson, lesson_id)
        if (not mod or not mod.is_published or not lesson or lesson.module_id != module_id
                or lesson.is_archived or mod.is_archived
                or (candidate_profile.industry_id and candidate_profile.industry_id != mod.industry_id)):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lesson or Module not found"
            )

        p_q = select(CandidateModuleProgress).where(
            CandidateModuleProgress.candidate_profile_id == candidate_profile.id,
            CandidateModuleProgress.module_id == module_id
        )
        p_res = await db.execute(p_q)
        prog = p_res.scalar_one_or_none()

        completed = await db.scalar(select(LessonProgress.id).where(
            LessonProgress.candidate_profile_id == candidate_profile.id,
            LessonProgress.lesson_id == lesson_id,
        ))
        if not completed:
            db.add(LessonProgress(candidate_profile_id=candidate_profile.id, lesson_id=lesson_id))

        await db.flush()

        lesson_count = await db.scalar(select(func.count(Lesson.id)).where(Lesson.module_id == module_id, Lesson.is_archived.is_(False)))
        completed_count = await db.scalar(select(func.count(LessonProgress.id)).join(
            Lesson, Lesson.id == LessonProgress.lesson_id
        ).where(
            LessonProgress.candidate_profile_id == candidate_profile.id,
            Lesson.module_id == module_id,
            Lesson.is_archived.is_(False),
        ))
        percentage = (completed_count / lesson_count * 100) if lesson_count else 0

        if not prog:
            prog = CandidateModuleProgress(
                candidate_profile_id=candidate_profile.id,
                module_id=module_id,
                status=ModuleProgressStatus.COMPLETED if percentage >= 100 else ModuleProgressStatus.IN_PROGRESS,
                completion_percentage=percentage,
                last_accessed_at=datetime.now(timezone.utc)
            )
            db.add(prog)
        else:
            prog.status = ModuleProgressStatus.COMPLETED if percentage >= 100 else ModuleProgressStatus.IN_PROGRESS
            prog.completion_percentage = percentage
            prog.last_accessed_at = datetime.now(timezone.utc)

        await db.commit()
        return await ModuleService.get_module_detail(db, module_id, candidate_profile)

    @staticmethod
    async def get_candidate_roadmap(
        db: AsyncSession,
        candidate_profile_id: uuid.UUID
    ) -> Optional[RoadmapResponse]:
        query = (
            select(Roadmap)
            .where(Roadmap.candidate_profile_id == candidate_profile_id)
            .options(selectinload(Roadmap.tasks))
            .order_by(Roadmap.created_at.desc())
        )
        result = await db.execute(query)
        roadmap = result.scalars().first()
        if not roadmap:
            return None
        return RoadmapResponse.model_validate(roadmap)

    @staticmethod
    async def toggle_roadmap_task(
        db: AsyncSession,
        task_id: uuid.UUID,
        candidate_profile_id: uuid.UUID
    ) -> RoadmapTaskResponse:
        query = (
            select(RoadmapTask)
            .join(Roadmap, RoadmapTask.roadmap_id == Roadmap.id)
            .where(
                RoadmapTask.id == task_id,
                Roadmap.candidate_profile_id == candidate_profile_id
            )
        )
        result = await db.execute(query)
        task = result.scalar_one_or_none()
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Roadmap task not found")

        task.is_completed = not task.is_completed
        await db.commit()
        await db.refresh(task)
        return RoadmapTaskResponse.model_validate(task)
