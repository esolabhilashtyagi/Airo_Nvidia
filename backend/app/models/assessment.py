import enum
import uuid
from typing import Optional
from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class AttemptStatus(str, enum.Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    TIMED_OUT = "timed_out"
    ABANDONED = "abandoned"


class Assessment(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "assessments"
    __table_args__ = (
        CheckConstraint(
            "candidate_profile_id IS NOT NULL OR is_active = false",
            name="ck_assessments_owner_required_when_active",
        ),
    )

    title: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    industry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("industries.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    job_role_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_roles.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    candidate_profile_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    difficulty: Mapped[str] = mapped_column(String(50), default="Intermediate", nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    total_questions: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    passing_percentage: Mapped[float] = mapped_column(Float, default=65.0, nullable=False)
    marks_per_question: Mapped[float] = mapped_column(Float, default=10.0, nullable=False)
    negative_marking_points: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    randomize_questions: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    industry = relationship("Industry")
    job_role = relationship("JobRole")
    questions = relationship("AssessmentQuestion", back_populates="assessment", cascade="all, delete-orphan", order_by="AssessmentQuestion.order_index")
    attempts = relationship("AssessmentAttempt", back_populates="assessment", cascade="all, delete-orphan")


class AssessmentQuestion(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "assessment_questions"

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    order_index: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Relationships
    assessment = relationship("Assessment", back_populates="questions")
    question = relationship("Question")


class AssessmentAttempt(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "assessment_attempts"

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    started_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[AttemptStatus] = mapped_column(
        Enum(AttemptStatus, name="attempt_status_enum", values_callable=lambda x: [e.value for e in x]),
        default=AttemptStatus.IN_PROGRESS,
        nullable=False
    )
    time_spent_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    assessment = relationship("Assessment", back_populates="attempts")
    candidate_profile = relationship("CandidateProfile", back_populates="assessment_attempts")
    answers = relationship("CandidateAnswer", back_populates="attempt", cascade="all, delete-orphan")
    result = relationship("AssessmentResult", back_populates="attempt", uselist=False, cascade="all, delete-orphan")


class CandidateAnswer(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "candidate_answers"

    assessment_attempt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assessment_attempts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    selected_options: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    text_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_marked_for_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_correct: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    score_awarded: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evaluation_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    evaluation_provenance: Mapped[str] = mapped_column(String(32), default="none", nullable=False)
    rubric_breakdown: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    missing_concepts: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    # Relationships
    attempt = relationship("AssessmentAttempt", back_populates="answers")
    question = relationship("Question")


class AssessmentResult(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "assessment_results"

    assessment_attempt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assessment_attempts.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )
    total_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    max_score: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    percentage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    passed: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    correct_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    incorrect_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unanswered_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    topic_breakdown: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    difficulty_breakdown: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    strong_areas: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    weak_areas: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    recommendations: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evaluation_status: Mapped[str] = mapped_column(String(32), default="complete", nullable=False)
    evaluation_provenance: Mapped[str] = mapped_column(String(32), default="deterministic", nullable=False)
    question_feedback: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    # Relationships
    attempt = relationship("AssessmentAttempt", back_populates="result")
