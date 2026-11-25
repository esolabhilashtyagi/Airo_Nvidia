import hashlib
import hmac
import json
from types import SimpleNamespace
import uuid

import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.services.ats_access import ATSAccessService


class FakeDB:
    def __init__(self, order):
        self.order = order
        self.commits = 0
        self.scalar_calls = 0

    async def scalar(self, _query):
        self.scalar_calls += 1
        return self.order

    async def commit(self):
        self.commits += 1


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeClient:
    def __init__(self, *, response):
        self.response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def get(self, *_args, **_kwargs):
        return self.response


def stored_order():
    return SimpleNamespace(
        user_id=uuid.uuid4(),
        razorpay_order_id="order_test_12345678",
        razorpay_payment_id=None,
        amount_paise=49900,
        currency="INR",
        status="created",
    )


def sign_checkout(order_id: str, payment_id: str, secret: str) -> str:
    return hmac.new(secret.encode(), f"{order_id}|{payment_id}".encode(), hashlib.sha256).hexdigest()


def sign_webhook(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@pytest.mark.asyncio
async def test_checkout_grants_access_only_after_matching_captured_payment(monkeypatch):
    secret = "synthetic-test-secret"
    order = stored_order()
    db = FakeDB(order)
    payment_id = "pay_test_12345678"
    monkeypatch.setattr(settings, "RAZORPAY_KEY_ID", "rzp_test_synthetic")
    monkeypatch.setattr(settings, "RAZORPAY_KEY_SECRET", secret)
    monkeypatch.setattr("app.services.ats_access.httpx.AsyncClient", lambda **_kwargs: FakeClient(response=FakeResponse({
        "id": payment_id,
        "order_id": order.razorpay_order_id,
        "amount": order.amount_paise,
        "currency": order.currency,
        "status": "captured",
        "captured": True,
    })))

    result = await ATSAccessService.verify_checkout(
        db, order.user_id, order.razorpay_order_id, payment_id,
        sign_checkout(order.razorpay_order_id, payment_id, secret),
    )

    assert result == {"has_access": True, "status": "captured"}
    assert order.razorpay_payment_id == payment_id
    assert order.status == "captured"
    assert db.commits == 1


@pytest.mark.asyncio
async def test_checkout_rejects_invalid_signature_without_querying_payment(monkeypatch):
    order = stored_order()
    db = FakeDB(order)
    monkeypatch.setattr(settings, "RAZORPAY_KEY_SECRET", "synthetic-test-secret")

    with pytest.raises(HTTPException) as error:
        await ATSAccessService.verify_checkout(
            db, order.user_id, order.razorpay_order_id, "pay_test_12345678", "bad-signature",
        )

    assert error.value.status_code == 400
    assert db.scalar_calls == 1
    assert db.commits == 0
    assert order.status == "created"


@pytest.mark.asyncio
async def test_checkout_does_not_unlock_for_amount_or_capture_mismatch(monkeypatch):
    secret = "synthetic-test-secret"
    order = stored_order()
    db = FakeDB(order)
    payment_id = "pay_test_12345678"
    monkeypatch.setattr(settings, "RAZORPAY_KEY_ID", "rzp_test_synthetic")
    monkeypatch.setattr(settings, "RAZORPAY_KEY_SECRET", secret)
    monkeypatch.setattr("app.services.ats_access.httpx.AsyncClient", lambda **_kwargs: FakeClient(response=FakeResponse({
        "id": payment_id,
        "order_id": order.razorpay_order_id,
        "amount": order.amount_paise - 100,
        "currency": order.currency,
        "status": "authorized",
        "captured": False,
    })))

    with pytest.raises(HTTPException) as error:
        await ATSAccessService.verify_checkout(
            db, order.user_id, order.razorpay_order_id, payment_id,
            sign_checkout(order.razorpay_order_id, payment_id, secret),
        )

    assert error.value.status_code == 409
    assert order.status == "created"
    assert db.commits == 0


@pytest.mark.asyncio
async def test_webhook_verifies_raw_body_signature_and_marks_only_matching_captured_order(monkeypatch):
    secret = "synthetic-webhook-secret"
    order = stored_order()
    db = FakeDB(order)
    body = json.dumps({
        "event": "order.paid",
        "payload": {"payment": {"entity": {
            "id": "pay_test_12345678",
            "order_id": order.razorpay_order_id,
            "amount": order.amount_paise,
            "currency": "INR",
            "status": "captured",
        }}},
    }).encode()
    monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", secret)

    result = await ATSAccessService.process_webhook(db, body, sign_webhook(body, secret))

    assert result == {"received": True}
    assert order.status == "captured"
    assert order.razorpay_payment_id == "pay_test_12345678"
    assert db.commits == 1


@pytest.mark.asyncio
async def test_webhook_rejects_bad_signature_before_parsing_or_mutating(monkeypatch):
    order = stored_order()
    db = FakeDB(order)
    monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", "synthetic-webhook-secret")

    with pytest.raises(HTTPException) as error:
        await ATSAccessService.process_webhook(db, b"{}", "bad-signature")

    assert error.value.status_code == 400
    assert db.scalar_calls == 0
    assert db.commits == 0
    assert order.status == "created"


def test_paid_ats_checkout_requires_an_explicit_positive_price(monkeypatch):
    monkeypatch.setattr(settings, "RAZORPAY_KEY_ID", "rzp_test_synthetic")
    monkeypatch.setattr(settings, "RAZORPAY_KEY_SECRET", "synthetic-test-secret")
    monkeypatch.setattr(settings, "ATS_ACCESS_PRICE_PAISE", 0)

    assert ATSAccessService.checkout_configured() is False

    monkeypatch.setattr(settings, "ATS_ACCESS_PRICE_PAISE", 100)
    assert ATSAccessService.checkout_configured() is True
