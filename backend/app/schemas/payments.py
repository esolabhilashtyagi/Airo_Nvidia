from pydantic import BaseModel, Field


class ATSAccessStatusResponse(BaseModel):
    has_access: bool
    price_paise: int
    currency: str = "INR"
    checkout_configured: bool


class ATSAccessOrderResponse(BaseModel):
    order_id: str
    key_id: str
    amount_paise: int
    currency: str = "INR"


class ATSAccessVerifyRequest(BaseModel):
    razorpay_order_id: str = Field(min_length=8, max_length=80)
    razorpay_payment_id: str = Field(min_length=8, max_length=80)
    razorpay_signature: str = Field(min_length=32, max_length=256)


class ResumeTemplatesStatusResponse(ATSAccessStatusResponse):
    pass
