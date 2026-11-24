import enum
import uuid
from typing import List, Optional
from sqlalchemy import Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class SuggestionStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class Resume(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "resumes"

    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    
    # Raw extracted text and parsed metadata
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parsed_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    original_parsed_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    parsing_status: Mapped[str] = mapped_column(String(50), default="uploaded", nullable=False)
    analysis_status: Mapped[str] = mapped_column(String(50), default="analysis_pending", nullable=False)
    extraction_confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    extraction_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    analysis_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    candidate_profile = relationship("CandidateProfile", back_populates="resumes")
    versions = relationship("ResumeVersion", back_populates="resume", cascade="all, delete-orphan")
    analyses = relationship("ResumeAnalysis", back_populates="resume", cascade="all, delete-orphan")
    # The database FK owns cascading deletion for ATS history. Keeping this
    # relationship passive avoids loading the optional table before deleting a
    # resume (for example, while an older schema is being migrated).
    ats_reviews = relationship(
        "ResumeATSReview", back_populates="resume", cascade="all, delete-orphan", passive_deletes=True
    )


class ResumeVersion(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "resume_versions"

    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    content: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    change_summary: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    resume = relationship("Resume", back_populates="versions")


class ResumeAnalysis(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "resume_analyses"

    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    overall_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    completeness_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    skills_relevance_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    experience_quality_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    target_role_alignment_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    formatting_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    category_scores: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    strengths: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    weaknesses: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    scoring_explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extraction_confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="analysis_completed", nullable=False)
    analysis_provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    professional_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary_analysis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    missing_keywords: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    improvement_opportunities: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    
    # Relationships
    resume = relationship("Resume", back_populates="analyses")
    suggestions = relationship("ResumeSuggestion", back_populates="analysis", cascade="all, delete-orphan")


class ResumeSuggestion(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "resume_suggestions"

    resume_analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resume_analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False) # e.g. Action Verbs, Keywords, Bullet Point
    original_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    suggested_text: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    supporting_context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[SuggestionStatus] = mapped_column(
        Enum(SuggestionStatus, name="suggestion_status_enum", values_callable=lambda x: [e.value for e in x]),
        default=SuggestionStatus.PENDING,
        nullable=False
    )

    # Relationships
    analysis = relationship("ResumeAnalysis", back_populates="suggestions")


class ResumeATSReview(Base, UUIDMixin, TimestampMixin):
    """Job-specific ATS compatibility estimate with an auditable score breakdown."""
    __tablename__ = "resume_ats_reviews"

    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_title: Mapped[str] = mapped_column(String(200), nullable=False)
    job_description: Mapped[str] = mapped_column(Text, nullable=False)
    ats_score: Mapped[float] = mapped_column(Float, nullable=False)
    keyword_match_score: Mapped[float] = mapped_column(Float, nullable=False)
    section_match_score: Mapped[float] = mapped_column(Float, nullable=False)
    matched_keywords: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    missing_keywords: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    matched_sections: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    missing_sections: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    formatting_warnings: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    resume = relationship("Resume", back_populates="ats_reviews")
