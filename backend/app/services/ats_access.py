"""Razorpay checkout and server-verified paid ATS entitlements."""

import hashlib
import hmac
import uuid
from typing import Any

import httpx
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.payment import ATSAccessPayment, ResumeTemplatePayment


class ATSAccessService:
    @staticmethod
    def checkout_configured() -> bool:
        return bool(
            settings.RAZORPAY_KEY_ID.strip()
            and settings.RAZORPAY_KEY_SECRET.strip()
            and settings.ATS_ACCESS_PRICE_PAISE > 0
        )

    @staticmethod
    async def has_access(db: AsyncSession, user_id: uuid.UUID) -> bool:
        payment_id = await db.scalar(select(ATSAccessPayment.id).where(
            ATSAccessPayment.user_id == user_id,
            ATSAccessPayment.status == "captured",
        ).limit(1))
        return payment_id is not None

    @staticmethod
    async def require_access(db: AsyncSession, user_id: uuid.UUID) -> None:
        if not await ATSAccessService.has_access(db, user_id):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Job-specific ATS review is a paid feature. Purchase ATS access to continue.",
            )

    @staticmethod
    async def status(db: AsyncSession, user_id: uuid.UUID) -> dict[str, Any]:
        return {
            "has_access": await ATSAccessService.has_access(db, user_id),
            "price_paise": max(0, int(settings.ATS_ACCESS_PRICE_PAISE)),
            "currency": "INR",
            "checkout_configured": ATSAccessService.checkout_configured(),
        }

    @staticmethod
    async def create_order(db: AsyncSession, user_id: uuid.UUID) -> dict[str, Any]:
        if await ATSAccessService.has_access(db, user_id):
            raise HTTPException(status_code=409, detail="Paid ATS access is already active for this account.")
        if not ATSAccessService.checkout_configured():
            raise HTTPException(status_code=503, detail="Paid ATS checkout is not configured yet.")

        amount = int(settings.ATS_ACCESS_PRICE_PAISE)
        receipt = f"ats_{uuid.uuid4().hex}"[:40]
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(
                    "https://api.razorpay.com/v1/orders",
                    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET),
                    json={
                        "amount": amount,
                        "currency": "INR",
                        "receipt": receipt,
                        "notes": {"product": "AAIRO paid ATS access", "user_reference": str(user_id)},
                    },
                )
                response.raise_for_status()
                order = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise HTTPException(status_code=502, detail="Razorpay could not create the payment order. Please retry.") from exc

        if not isinstance(order, dict):
            raise HTTPException(status_code=502, detail="Razorpay returned an invalid order response. No payment was opened.")
        order_id = order.get("id")
        if (
            not isinstance(order_id, str)
            or not order_id.startswith("order_")
            or order.get("amount") != amount
            or order.get("currency") != "INR"
        ):
            raise HTTPException(status_code=502, detail="Razorpay returned an invalid order. No payment was opened.")
        db.add(ATSAccessPayment(
            user_id=user_id,
            razorpay_order_id=order_id,
            amount_paise=amount,
            currency="INR",
            status="created",
        ))
        await db.commit()
        return {"order_id": order_id, "key_id": settings.RAZORPAY_KEY_ID, "amount_paise": amount, "currency": "INR"}

    @staticmethod
    async def verify_checkout(
        db: AsyncSession,
        user_id: uuid.UUID,
        order_id: str,
        payment_id: str,
        signature: str,
    ) -> dict[str, Any]:
        if not settings.RAZORPAY_KEY_SECRET.strip():
            raise HTTPException(status_code=503, detail="Payment verification is not configured.")
        order = await db.scalar(select(ATSAccessPayment).where(
            ATSAccessPayment.razorpay_order_id == order_id,
            ATSAccessPayment.user_id == user_id,
        ).with_for_update())
        if not order:
            raise HTTPException(status_code=404, detail="Payment order not found for this account.")
        if order.status == "captured" and order.razorpay_payment_id == payment_id:
            return {"has_access": True, "status": "captured"}

        expected = hmac.new(
            settings.RAZORPAY_KEY_SECRET.encode(),
            f"{order.razorpay_order_id}|{payment_id}".encode(),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise HTTPException(status_code=400, detail="Payment signature could not be verified.")

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(
                    f"https://api.razorpay.com/v1/payments/{payment_id}",
                    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET),
                )
                response.raise_for_status()
                payment = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise HTTPException(status_code=502, detail="Razorpay payment status could not be confirmed. Retry shortly.") from exc
        if not isinstance(payment, dict):
            raise HTTPException(status_code=502, detail="Razorpay returned an invalid payment response. Access remains locked.")
        if (
            payment.get("order_id") != order.razorpay_order_id
            or payment.get("amount") != order.amount_paise
            or payment.get("currency") != order.currency
            or payment.get("status") != "captured"
            or payment.get("captured") is not True
        ):
            raise HTTPException(status_code=409, detail="Payment is not captured for this order yet. Access remains locked until confirmation.")
        order.razorpay_payment_id = payment_id
        order.status = "captured"
        await db.commit()
        return {"has_access": True, "status": "captured"}

    @staticmethod
    async def process_webhook(db: AsyncSession, body: bytes, signature: str | None) -> dict[str, bool]:
        secret = settings.RAZORPAY_WEBHOOK_SECRET.strip()
        if not secret or not signature:
            raise HTTPException(status_code=503, detail="Payment webhook verification is not configured.")
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise HTTPException(status_code=400, detail="Invalid Razorpay webhook signature.")
        try:
            import json
            event = json.loads(body)
        except (ValueError, UnicodeDecodeError) as exc:
            raise HTTPException(status_code=400, detail="Invalid Razorpay webhook body.") from exc
        if not isinstance(event, dict):
            raise HTTPException(status_code=400, detail="Invalid Razorpay webhook event.")
        if event.get("event") != "order.paid":
            return {"received": True}
        payload = event.get("payload")
        payment_event = payload.get("payment") if isinstance(payload, dict) else None
        payment = payment_event.get("entity") if isinstance(payment_event, dict) else None
        if not isinstance(payment, dict):
            raise HTTPException(status_code=400, detail="Razorpay paid event is missing its payment record.")
        order_id = payment.get("order_id")
        payment_id = payment.get("id")
        if not isinstance(order_id, str) or not isinstance(payment_id, str):
            raise HTTPException(status_code=400, detail="Razorpay paid event is missing payment identifiers.")
        order = await db.scalar(select(ATSAccessPayment).where(
            ATSAccessPayment.razorpay_order_id == order_id,
        ).with_for_update())
        if not order:
            resume_order = await db.scalar(select(ResumeTemplatePayment).where(
                ResumeTemplatePayment.razorpay_order_id == order_id,
            ).with_for_update())
            if not resume_order:
                return {"received": True}
            if payment.get("status") != "captured" or payment.get("amount") != resume_order.amount_paise or payment.get("currency") != resume_order.currency:
                raise HTTPException(status_code=409, detail="Paid event does not match the stored resume order amount or capture state.")
            if resume_order.status != "captured":
                resume_order.razorpay_payment_id = payment_id
                resume_order.status = "captured"
                await db.commit()
            return {"received": True}
        # A valid payment for an unrelated product/order is acknowledged, not granted.
        if (
            payment.get("status") != "captured"
            or payment.get("amount") != order.amount_paise
            or payment.get("currency") != order.currency
        ):
            raise HTTPException(status_code=409, detail="Paid event does not match the stored order amount or capture state.")
        if order.status != "captured":
            order.razorpay_payment_id = payment_id
            order.status = "captured"
            await db.commit()
        return {"received": True}
