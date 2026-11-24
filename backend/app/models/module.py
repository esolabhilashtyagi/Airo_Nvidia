import enum
import uuid
from typing import Optional
from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, String, Table, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin


module_job_roles = Table(
    "module_job_roles", Base.metadata,
    Column("module_id", UUID(as_uuid=True), ForeignKey("modules.id", ondelete="CASCADE"), primary_key=True),
    Column("job_role_id", UUID(as_uuid=True), ForeignKey("job_roles.id", ondelete="RESTRICT"), primary_key=True),
)
module_skills = Table(
    "module_skills", Base.metadata,
    Column("module_id", UUID(as_uuid=True), ForeignKey("modules.id", ondelete="CASCADE"), primary_key=True),
    Column("skill_id", UUID(as_uuid=True), ForeignKey("skills.id", ondelete="RESTRICT"), primary_key=True),
)


class ModuleProgressStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class Module(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "modules"

    industry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("industries.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    title: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(50), default="Intermediate", nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    # Relationships
    industry = relationship("Industry", back_populates="modules")
    lessons = relationship("Lesson", back_populates="module", cascade="all, delete-orphan", order_by="Lesson.order_index")
    candidate_progress = relationship("CandidateModuleProgress", back_populates="module", cascade="all, delete-orphan")
    job_roles = relationship("JobRole", secondary=module_job_roles, back_populates="modules")
    skills = relationship("Skill", secondary=module_skills, back_populates="modules")

    @property
    def job_role_ids(self):
        return [role.id for role in self.job_roles]

    @property
    def skill_ids(self):
        return [skill.id for skill in self.skills]


class Lesson(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "lessons"

    module_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("modules.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    # Relationships
    module = relationship("Module", back_populates="lessons")


class CandidateModuleProgress(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "candidate_module_progress"
    __table_args__ = (UniqueConstraint("candidate_profile_id", "module_id", name="uq_candidate_module_progress"),)

    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    module_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("modules.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    status: Mapped[ModuleProgressStatus] = mapped_column(
        Enum(ModuleProgressStatus, name="module_progress_status_enum", values_callable=lambda x: [e.value for e in x]),
        default=ModuleProgressStatus.NOT_STARTED,
        nullable=False
    )
    completion_percentage: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    last_accessed_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    candidate_profile = relationship("CandidateProfile", back_populates="module_progress")
    module = relationship("Module", back_populates="candidate_progress")


class LessonProgress(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "lesson_progress"
    __table_args__ = (UniqueConstraint("candidate_profile_id", "lesson_id", name="uq_lesson_progress_candidate_lesson"),)

    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    lesson_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True
    )


class Roadmap(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "roadmaps"

    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)

    # Relationships
    candidate_profile = relationship("CandidateProfile", back_populates="roadmaps")
    tasks = relationship("RoadmapTask", back_populates="roadmap", cascade="all, delete-orphan", order_by="RoadmapTask.order_index")


class RoadmapTask(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "roadmap_tasks"

    roadmap_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roadmaps.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    module_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("modules.id", ondelete="SET NULL"),
        nullable=True
    )
    order_index: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    roadmap = relationship("Roadmap", back_populates="tasks")
    module = relationship("Module")
