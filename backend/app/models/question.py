import enum
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, String, Table, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin


question_job_roles = Table(
    "question_job_roles", Base.metadata,
    Column("question_id", UUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True),
    Column("job_role_id", UUID(as_uuid=True), ForeignKey("job_roles.id", ondelete="RESTRICT"), primary_key=True),
)
question_skills = Table(
    "question_skills", Base.metadata,
    Column("question_id", UUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True),
    Column("skill_id", UUID(as_uuid=True), ForeignKey("skills.id", ondelete="RESTRICT"), primary_key=True),
)
question_companies = Table(
    "question_companies", Base.metadata,
    Column("question_id", UUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True),
    Column("company_id", UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), primary_key=True),
)


class QuestionType(str, enum.Enum):
    MCQ_SINGLE = "mcq_single"
    MCQ_MULTIPLE = "mcq_multiple"
    SHORT_ANSWER = "short_answer"
    LONG_ANSWER = "long_answer"
    DESCRIPTIVE = "descriptive"
    CODING = "coding"
    SCENARIO = "scenario"
    CASE_STUDY = "case_study"
    SITUATIONAL = "situational"
    BEHAVIORAL = "behavioral"
    TECHNICAL = "technical"
    DOMAIN_SPECIFIC = "domain_specific"


class DifficultyLevel(str, enum.Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class SourceProvenance(str, enum.Enum):
    SOURCE_VERIFIED = "source_verified"
    SOURCE_FORMATTED = "source_formatted"
    AI_GENERATED = "ai_generated"
    EDITORIALLY_REVIEWED = "editorially_reviewed"


class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Question(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "questions"
    __table_args__ = (UniqueConstraint("root_question_id", "version_number", name="uq_question_revision_number"),)

    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[QuestionType] = mapped_column(
        Enum(QuestionType, name="question_type_enum", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True
    )
    industry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("industries.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    industry_category_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("industry_categories.id", ondelete="SET NULL"), nullable=True, index=True)
    subject_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True, index=True)
    topic_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("topics.id", ondelete="SET NULL"), nullable=True, index=True)
    experience_level_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("experience_levels.id", ondelete="SET NULL"), nullable=True, index=True)
    interview_round_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("interview_rounds.id", ondelete="SET NULL"), nullable=True, index=True)
    experience_level: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    job_role_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_roles.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    subject: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    topic: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    difficulty: Mapped[DifficultyLevel] = mapped_column(
        Enum(DifficultyLevel, name="difficulty_level_enum", values_callable=lambda x: [e.value for e in x]),
        default=DifficultyLevel.INTERMEDIATE,
        nullable=False,
        index=True
    )
    interview_round: Mapped[str] = mapped_column(String(100), default="Technical", nullable=False, index=True)
    
    # MCQ options: [{"id": "A", "text": "Option A", "is_correct": True}, ...]
    options: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    expected_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evaluation_rubric: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    tags: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    
    source_provenance: Mapped[SourceProvenance] = mapped_column(
        Enum(SourceProvenance, name="source_provenance_enum", values_callable=lambda x: [e.value for e in x]),
        default=SourceProvenance.SOURCE_VERIFIED,
        nullable=False
    )
    approval_status: Mapped[ApprovalStatus] = mapped_column(
        Enum(ApprovalStatus, name="approval_status_enum", values_callable=lambda x: [e.value for e in x]),
        default=ApprovalStatus.APPROVED,
        nullable=False,
        index=True
    )
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    marks: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    estimated_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    workflow_status: Mapped[str] = mapped_column(String(32), default="pending_review", nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    root_question_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("questions.id", ondelete="RESTRICT"), nullable=True, index=True)
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    review_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    industry = relationship("Industry", back_populates="questions")
    job_role = relationship("JobRole", foreign_keys=[job_role_id])
    job_roles = relationship("JobRole", secondary=question_job_roles, back_populates="question_versions")
    industry_category = relationship("IndustryCategory", back_populates="questions")
    subject_taxonomy = relationship("Subject", back_populates="questions")
    topic_taxonomy = relationship("Topic", back_populates="questions")
    experience_taxonomy = relationship("ExperienceLevel")
    round_taxonomy = relationship("InterviewRound")
    skills = relationship("Skill", secondary=question_skills, back_populates="questions")
    companies = relationship("Company", secondary=question_companies)
    root_question = relationship("Question", remote_side="Question.id", foreign_keys=[root_question_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])
    bookmarks = relationship("QuestionBookmark", back_populates="question", cascade="all, delete-orphan")
    practice_logs = relationship("QuestionPracticeLog", back_populates="question", cascade="all, delete-orphan")


class QuestionBookmark(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "question_bookmarks"
    __table_args__ = (UniqueConstraint("candidate_profile_id", "question_id", name="uq_question_bookmark_candidate_question"),)

    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Relationships
    candidate_profile = relationship("CandidateProfile", back_populates="bookmarks")
    question = relationship("Question", back_populates="bookmarks")


class QuestionPracticeLog(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "question_practice_logs"

    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_response: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    score_percentage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ai_feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evaluation_status: Mapped[str] = mapped_column(String(32), default="evaluated", nullable=False)
    evaluation_provenance: Mapped[str] = mapped_column(String(32), default="deterministic", nullable=False)

    # Relationships
    candidate_profile = relationship("CandidateProfile", back_populates="practice_logs")
    question = relationship("Question", back_populates="practice_logs")
