"""One-time Razorpay unlock for premium profile resume layouts."""

import hashlib
import hmac
import uuid
from typing import Any

import httpx
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.payment import ResumeTemplatePayment


class ResumeTemplateAccessService:
    @staticmethod
    def checkout_configured() -> bool:
        return bool(settings.RAZORPAY_KEY_ID.strip() and settings.RAZORPAY_KEY_SECRET.strip() and settings.RESUME_TEMPLATES_PRICE_PAISE > 0)

    @staticmethod
    async def has_access(db: AsyncSession, user_id: uuid.UUID) -> bool:
        return await db.scalar(select(ResumeTemplatePayment.id).where(
            ResumeTemplatePayment.user_id == user_id,
            ResumeTemplatePayment.status == "captured",
        ).limit(1)) is not None

    @staticmethod
    async def status(db: AsyncSession, user_id: uuid.UUID) -> dict[str, Any]:
        return {
            "has_access": await ResumeTemplateAccessService.has_access(db, user_id),
            "price_paise": max(0, int(settings.RESUME_TEMPLATES_PRICE_PAISE)),
            "currency": "INR",
            "checkout_configured": ResumeTemplateAccessService.checkout_configured(),
        }

    @staticmethod
    async def create_order(db: AsyncSession, user_id: uuid.UUID) -> dict[str, Any]:
        if await ResumeTemplateAccessService.has_access(db, user_id):
            raise HTTPException(status_code=409, detail="Premium resume layouts are already unlocked for this account.")
        if not ResumeTemplateAccessService.checkout_configured():
            raise HTTPException(status_code=503, detail="Premium resume checkout is not configured yet.")
        amount = int(settings.RESUME_TEMPLATES_PRICE_PAISE)
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(
                    "https://api.razorpay.com/v1/orders",
                    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET),
                    json={"amount": amount, "currency": "INR", "receipt": f"resume_{uuid.uuid4().hex}"[:40],
                          "notes": {"product": "AAIRO premium resume templates", "user_reference": str(user_id)}},
                )
                response.raise_for_status()
                order = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise HTTPException(status_code=502, detail="Payment provider could not create the order. Please retry.") from exc
        order_id = order.get("id") if isinstance(order, dict) else None
        if not isinstance(order_id, str) or not order_id.startswith("order_") or order.get("amount") != amount or order.get("currency") != "INR":
            raise HTTPException(status_code=502, detail="Payment provider returned an invalid order.")
        db.add(ResumeTemplatePayment(user_id=user_id, razorpay_order_id=order_id, amount_paise=amount, currency="INR", status="created"))
        await db.commit()
        return {"order_id": order_id, "key_id": settings.RAZORPAY_KEY_ID, "amount_paise": amount, "currency": "INR"}

    @staticmethod
    async def verify_checkout(db: AsyncSession, user_id: uuid.UUID, order_id: str, payment_id: str, signature: str) -> dict[str, Any]:
        if not settings.RAZORPAY_KEY_SECRET.strip():
            raise HTTPException(status_code=503, detail="Payment verification is not configured.")
        order = await db.scalar(select(ResumeTemplatePayment).where(
            ResumeTemplatePayment.razorpay_order_id == order_id,
            ResumeTemplatePayment.user_id == user_id,
        ).with_for_update())
        if not order:
            raise HTTPException(status_code=404, detail="Payment order not found for this account.")
        if order.status == "captured" and order.razorpay_payment_id == payment_id:
            return {"has_access": True, "status": "captured"}
        expected = hmac.new(settings.RAZORPAY_KEY_SECRET.encode(), f"{order_id}|{payment_id}".encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise HTTPException(status_code=400, detail="Payment signature could not be verified.")
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(f"https://api.razorpay.com/v1/payments/{payment_id}", auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
                response.raise_for_status()
                payment = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise HTTPException(status_code=502, detail="Payment status could not be confirmed. Retry shortly.") from exc
        if not isinstance(payment, dict) or payment.get("order_id") != order_id or payment.get("amount") != order.amount_paise or payment.get("currency") != order.currency or payment.get("status") != "captured" or payment.get("captured") is not True:
            raise HTTPException(status_code=409, detail="Payment is not captured for this order. Access remains locked.")
        order.razorpay_payment_id = payment_id
        order.status = "captured"
        await db.commit()
        return {"has_access": True, "status": "captured"}
