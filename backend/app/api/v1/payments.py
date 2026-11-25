from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_async_db
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.payments import ATSAccessOrderResponse, ATSAccessStatusResponse, ATSAccessVerifyRequest
from app.services.ats_access import ATSAccessService
from app.services.resume_template_access import ResumeTemplateAccessService

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.get("/ats-access", response_model=APIResponse[ATSAccessStatusResponse])
async def get_ats_access(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    return APIResponse(data=await ATSAccessService.status(db, current_user.id), message="Paid ATS access status retrieved")


@router.get("/resume-templates", response_model=APIResponse[ATSAccessStatusResponse])
async def get_resume_template_access(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    return APIResponse(data=await ResumeTemplateAccessService.status(db, current_user.id), message="Resume template access retrieved")


@router.post("/resume-templates/order", response_model=APIResponse[ATSAccessOrderResponse])
async def create_resume_template_order(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    return APIResponse(data=await ResumeTemplateAccessService.create_order(db, current_user.id), message="Resume template order created")


@router.post("/resume-templates/verify", response_model=APIResponse[dict])
async def verify_resume_template_payment(
    payload: ATSAccessVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    result = await ResumeTemplateAccessService.verify_checkout(db, current_user.id, payload.razorpay_order_id, payload.razorpay_payment_id, payload.razorpay_signature)
    return APIResponse(data=result, message="Payment verified and resume layouts unlocked")


@router.post("/ats-access/order", response_model=APIResponse[ATSAccessOrderResponse])
async def create_ats_access_order(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    order = await ATSAccessService.create_order(db, current_user.id)
    return APIResponse(data=order, message="Razorpay order created")


@router.post("/ats-access/verify", response_model=APIResponse[dict])
async def verify_ats_access_payment(
    payload: ATSAccessVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    result = await ATSAccessService.verify_checkout(
        db,
        current_user.id,
        payload.razorpay_order_id,
        payload.razorpay_payment_id,
        payload.razorpay_signature,
    )
    return APIResponse(data=result, message="Payment verified and ATS access updated")


@router.post("/razorpay/webhook", response_model=APIResponse[dict])
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str | None = Header(default=None),
    db: AsyncSession = Depends(get_async_db),
):
    body = await request.body()
    if len(body) > 1_000_000:
        from fastapi import HTTPException
        raise HTTPException(status_code=413, detail="Webhook body is too large.")
    result = await ATSAccessService.process_webhook(db, body, x_razorpay_signature)
    return APIResponse(data=result, message="Razorpay webhook received")
