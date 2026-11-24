import enum
import uuid
from typing import Optional
from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class InterviewStatus(str, enum.Enum):
    SETUP = "setup"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class MockInterview(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "mock_interviews"

    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    industry_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("industries.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    job_role: Mapped[str] = mapped_column(String(255), nullable=False)
    interview_type: Mapped[str] = mapped_column(String(50), default="complete", nullable=False)
    target_company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    interview_round: Mapped[str] = mapped_column(String(100), default="Technical", nullable=False)
    difficulty: Mapped[str] = mapped_column(String(50), default="Intermediate", nullable=False)
    experience_level: Mapped[str] = mapped_column(String(50), default="Mid-Level", nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    total_questions: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    mode: Mapped[str] = mapped_column(String(20), default="text", nullable=False) # text or voice
    status: Mapped[InterviewStatus] = mapped_column(
        Enum(InterviewStatus, name="interview_status_enum", values_callable=lambda x: [e.value for e in x]),
        default=InterviewStatus.SETUP,
        nullable=False
    )
    evaluation_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    started_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    candidate_profile = relationship("CandidateProfile", back_populates="mock_interviews")
    industry = relationship("Industry")
    questions = relationship("InterviewQuestion", back_populates="interview", cascade="all, delete-orphan", order_by="InterviewQuestion.order_index")
    evaluation = relationship("InterviewEvaluation", back_populates="interview", uselist=False, cascade="all, delete-orphan")


class InterviewQuestion(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "interview_questions"

    mock_interview_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("mock_interviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_question_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("questions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_provenance: Mapped[str] = mapped_column(String(32), default="question_bank", nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_follow_up: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    parent_question_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_questions.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    interview = relationship("MockInterview", back_populates="questions")
    response = relationship("InterviewResponse", back_populates="question", uselist=False, cascade="all, delete-orphan")


class InterviewResponse(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "interview_responses"

    interview_question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_questions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )
    candidate_answer: Mapped[str] = mapped_column(Text, nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    question = relationship("InterviewQuestion", back_populates="response")


class InterviewEvaluation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "interview_evaluations"

    mock_interview_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("mock_interviews.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )
    overall_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    technical_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    domain_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    communication_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    structure_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    evaluation_status: Mapped[str] = mapped_column(String(32), default="unavailable", nullable=False)
    evaluation_provenance: Mapped[str] = mapped_column(String(32), default="none", nullable=False)
    
    key_strengths: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    improvement_areas: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    detailed_feedback: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    question_evaluations: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    # Relationships
    interview = relationship("MockInterview", back_populates="evaluation")
