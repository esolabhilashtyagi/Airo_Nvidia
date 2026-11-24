import uuid
from typing import List, Optional
from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class CandidateProfile(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "candidate_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False
    )
    # working_professional or student_fresher
    candidate_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    sub_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    industry_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("industries.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    current_company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    current_role: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    target_role: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    total_experience_months: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    relevant_experience_months: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    employment_status: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    key_skills: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    career_goals: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Onboarding progression
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    onboarding_step: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # Preferences
    interview_rounds_preferred: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    interaction_preference: Mapped[str] = mapped_column(String(20), default="text", nullable=False) # text or voice
    
    # Analytics readiness (0.0 to 100.0)
    interview_readiness_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Relationships
    user = relationship("User", back_populates="candidate_profile")
    industry = relationship("Industry")
    education_history = relationship("Education", back_populates="candidate_profile", cascade="all, delete-orphan")
    experience_history = relationship("ProfessionalExperience", back_populates="candidate_profile", cascade="all, delete-orphan")
    target_companies = relationship("CandidateTargetCompany", back_populates="candidate_profile", cascade="all, delete-orphan")
    resumes = relationship("Resume", back_populates="candidate_profile", cascade="all, delete-orphan")
    roadmaps = relationship("Roadmap", back_populates="candidate_profile", cascade="all, delete-orphan")
    module_progress = relationship("CandidateModuleProgress", back_populates="candidate_profile", cascade="all, delete-orphan")
    assessment_attempts = relationship("AssessmentAttempt", back_populates="candidate_profile", cascade="all, delete-orphan")
    mock_interviews = relationship("MockInterview", back_populates="candidate_profile", cascade="all, delete-orphan")
    coach_conversations = relationship("CoachConversation", back_populates="candidate_profile", cascade="all, delete-orphan")
    bookmarks = relationship("QuestionBookmark", back_populates="candidate_profile", cascade="all, delete-orphan")
    practice_logs = relationship("QuestionPracticeLog", back_populates="candidate_profile", cascade="all, delete-orphan")


class Education(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "education"

    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    degree: Mapped[str] = mapped_column(String(100), nullable=False) # e.g. B.Tech, MBA
    field_of_study: Mapped[str] = mapped_column(String(255), nullable=False) # e.g. Computer Science
    institution: Mapped[str] = mapped_column(String(255), nullable=False)
    start_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    end_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    grade: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    candidate_profile = relationship("CandidateProfile", back_populates="education_history")


class ProfessionalExperience(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "professional_experience"

    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    job_title: Mapped[str] = mapped_column(String(255), nullable=False)
    start_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    end_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    candidate_profile = relationship("CandidateProfile", back_populates="experience_history")


class Company(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    industry: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class CandidateTargetCompany(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "candidate_target_companies"

    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    target_role: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    candidate_profile = relationship("CandidateProfile", back_populates="target_companies")
    company = relationship("Company")
