import uuid
from typing import Any, Dict, List
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.core.database import get_async_db
from app.models.assessment import Assessment
from app.models.candidate import CandidateProfile
from app.models.module import Module
from app.models.question import Question
from app.models.taxonomy import Industry, JobRole
from app.models.user import User, UserRole
from app.schemas.auth import UserResponse
from app.schemas.common import APIResponse

router = APIRouter(prefix="/admin", tags=["Administration"])


class UserActiveRequest(BaseModel):
    is_active: bool


@router.get("/stats", response_model=APIResponse[Dict[str, Any]])
async def get_admin_stats(
    _auth = Depends(require_role([UserRole.ADMINISTRATOR, UserRole.CONTENT_MANAGER])),
    db: AsyncSession = Depends(get_async_db)
):
    users_count = (await db.execute(select(func.count(User.id)))).scalar_one()
    candidates_count = (await db.execute(select(func.count(CandidateProfile.id)))).scalar_one()
    industries_count = (await db.execute(select(func.count(Industry.id)))).scalar_one()
    roles_count = (await db.execute(select(func.count(JobRole.id)))).scalar_one()
    questions_count = (await db.execute(select(func.count(Question.id)))).scalar_one()
    modules_count = (await db.execute(select(func.count(Module.id)))).scalar_one()
    assessments_count = (await db.execute(select(func.count(Assessment.id)))).scalar_one()

    stats = {
        "total_users": users_count,
        "total_candidates": candidates_count,
        "total_industries": industries_count,
        "total_job_roles": roles_count,
        "total_questions": questions_count,
        "total_modules": modules_count,
        "total_assessments": assessments_count
    }
    return APIResponse(data=stats, message="Platform administration statistics retrieved")


@router.get("/users", response_model=APIResponse[List[UserResponse]])
async def list_users(
    _auth = Depends(require_role([UserRole.ADMINISTRATOR])),
    db: AsyncSession = Depends(get_async_db)
):
    result = await db.execute(select(User).order_by(User.created_at.desc()).limit(100))
    users = result.scalars().all()
    output = [
        UserResponse(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            role=u.role,
            is_active=u.is_active,
            is_verified=u.is_verified,
            created_at=u.created_at,
            updated_at=u.updated_at
        )
        for u in users
    ]
    return APIResponse(data=output, message="Users list retrieved")


@router.patch("/users/{user_id}/active", response_model=APIResponse[UserResponse])
async def set_user_active(
    user_id: uuid.UUID,
    request: UserActiveRequest,
    auth=Depends(require_role([UserRole.ADMINISTRATOR])),
    db: AsyncSession = Depends(get_async_db),
):
    # Serialize role-status changes while checking the last administrator so
    # concurrent deactivation requests cannot both pass the count check.
    await db.scalars(select(User.id).where(User.role == UserRole.ADMINISTRATOR)
        .order_by(User.id).with_for_update())
    target = await db.scalar(select(User).where(User.id == user_id).with_for_update())
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.id == auth.id and not request.is_active:
        raise HTTPException(status_code=409, detail="Administrators cannot deactivate their own account")
    if target.role == UserRole.ADMINISTRATOR and target.is_active and not request.is_active:
        active_admins = await db.scalar(select(func.count(User.id)).where(
            User.role == UserRole.ADMINISTRATOR,
            User.is_active.is_(True),
        ))
        if (active_admins or 0) <= 1:
            raise HTTPException(status_code=409, detail="The last active administrator cannot be deactivated")
    target.is_active = request.is_active
    await db.commit()
    await db.refresh(target)
    return APIResponse(data=UserResponse.model_validate(target), message="User account status updated")
