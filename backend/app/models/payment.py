import uuid

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class ATSAccessPayment(Base, UUIDMixin, TimestampMixin):
    """Server-verified Razorpay purchase record for the paid ATS add-on."""

    __tablename__ = "ats_access_payments"
    __table_args__ = (
        UniqueConstraint("razorpay_order_id", name="uq_ats_access_payment_order"),
        UniqueConstraint("razorpay_payment_id", name="uq_ats_access_payment_payment"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    razorpay_order_id: Mapped[str] = mapped_column(String(80), nullable=False)
    razorpay_payment_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    amount_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="created")


class ResumeTemplatePayment(Base, UUIDMixin, TimestampMixin):
    """Server-verified one-time unlock for premium profile resume layouts."""

    __tablename__ = "resume_template_payments"
    __table_args__ = (
        UniqueConstraint("razorpay_order_id", name="uq_resume_template_payment_order"),
        UniqueConstraint("razorpay_payment_id", name="uq_resume_template_payment_payment"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    razorpay_order_id: Mapped[str] = mapped_column(String(80), nullable=False)
    razorpay_payment_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    amount_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="created")
