import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_async_db
from app.models.system import Notification
from app.models.user import User
from app.schemas.common import APIResponse
from app.integrations.ai.provider_factory import get_ai_provider

router = APIRouter(prefix="/system", tags=["System"])


@router.get("/ai-status", response_model=APIResponse[dict])
async def ai_status():
    provider = get_ai_provider()
    return APIResponse(data={
        "provider": provider.provider_name,
        "model": provider.model_name,
        "configured": provider.is_available(),
    }, message="AI provider configuration status retrieved")


@router.get("/notifications", response_model=APIResponse[list[dict]])
async def list_notifications(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_async_db)):
    rows = await db.scalars(select(Notification).where(Notification.user_id == user.id).order_by(Notification.created_at.desc()).limit(50))
    return APIResponse(data=[{"id": row.id, "title": row.title, "message": row.message, "type": row.type, "is_read": row.is_read, "link_url": row.link_url, "created_at": row.created_at} for row in rows.all()], message="Notifications retrieved")


@router.patch("/notifications/{notification_id}/read", response_model=APIResponse[dict])
async def mark_notification_read(notification_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_async_db)):
    row = await db.scalar(select(Notification).where(Notification.id == notification_id, Notification.user_id == user.id).with_for_update())
    if not row:
        raise HTTPException(status_code=404, detail="Notification not found")
    row.is_read = True
    await db.commit()
    return APIResponse(data={"id": row.id, "is_read": row.is_read}, message="Notification marked as read")
