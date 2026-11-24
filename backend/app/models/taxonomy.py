import uuid
from typing import List, Optional
from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class Industry(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "industries"

    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    icon: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    categories = relationship("IndustryCategory", back_populates="industry")
    job_roles = relationship("JobRole", back_populates="industry")
    modules = relationship("Module", back_populates="industry")
    questions = relationship("Question", back_populates="industry")


class IndustryCategory(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "industry_categories"
    __table_args__ = (UniqueConstraint("industry_id", "name", name="uq_industry_category_name"),)

    industry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("industries.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    industry = relationship("Industry", back_populates="categories")
    questions = relationship("Question", back_populates="industry_category")


class Subject(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "subjects"
    __table_args__ = (UniqueConstraint("industry_id", "name", name="uq_subject_industry_name"),)
    industry_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("industries.id", ondelete="RESTRICT"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    industry = relationship("Industry")
    topics = relationship("Topic", back_populates="subject", cascade="all, delete-orphan")
    questions = relationship("Question", back_populates="subject_taxonomy")


class Topic(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "topics"
    __table_args__ = (UniqueConstraint("subject_id", "name", name="uq_topic_subject_name"),)
    subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    subject = relationship("Subject", back_populates="topics")
    questions = relationship("Question", back_populates="topic_taxonomy")


class ExperienceLevel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "experience_levels"
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class InterviewRound(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "interview_rounds"
    __table_args__ = (UniqueConstraint("industry_id", "name", name="uq_interview_round_industry_name"),)
    industry_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("industries.id", ondelete="RESTRICT"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    industry = relationship("Industry")


class JobRole(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "job_roles"

    industry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("industries.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    title: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    experience_level: Mapped[str] = mapped_column(String(50), default="All Levels", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    industry = relationship("Industry", back_populates="job_roles")
    question_versions = relationship("Question", secondary="question_job_roles", back_populates="job_roles")
    modules = relationship("Module", secondary="module_job_roles", back_populates="job_roles")


class Skill(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "skills"

    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_technical: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    questions = relationship("Question", secondary="question_skills", back_populates="skills")
    modules = relationship("Module", secondary="module_skills", back_populates="skills")
