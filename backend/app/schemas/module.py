import uuid
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.module import ModuleProgressStatus


class LessonResponse(BaseModel):
    id: uuid.UUID
    module_id: uuid.UUID
    title: str
    content: str
    duration_minutes: int
    order_index: int
    is_archived: bool = False

    model_config = ConfigDict(from_attributes=True)


class ModuleResponse(BaseModel):
    id: uuid.UUID
    industry_id: uuid.UUID
    title: str
    description: str
    difficulty: str
    duration_minutes: int
    order_index: int
    is_published: bool
    is_archived: bool = False
    lessons: List[LessonResponse] = Field(default_factory=list)
    job_role_ids: List[uuid.UUID] = Field(default_factory=list)
    skill_ids: List[uuid.UUID] = Field(default_factory=list)
    completed_lesson_ids: List[uuid.UUID] = Field(default_factory=list)
    progress_status: ModuleProgressStatus = ModuleProgressStatus.NOT_STARTED
    completion_percentage: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class RoadmapTaskResponse(BaseModel):
    id: uuid.UUID
    roadmap_id: uuid.UUID
    title: str
    description: Optional[str] = None
    module_id: Optional[uuid.UUID] = None
    order_index: int
    is_completed: bool

    model_config = ConfigDict(from_attributes=True)


class RoadmapResponse(BaseModel):
    id: uuid.UUID
    candidate_profile_id: uuid.UUID
    title: str
    description: Optional[str] = None
    status: str
    tasks: List[RoadmapTaskResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

class ModuleManageCreate(BaseModel):
    industry_id: uuid.UUID
    title: str = Field(min_length=3, max_length=255)
    description: str = Field(min_length=5)
    difficulty: str = Field(default="Intermediate", max_length=50)
    duration_minutes: int = Field(default=60, ge=1, le=10000)
    order_index: int = Field(default=1, ge=1)
    is_published: bool = False
    job_role_ids: List[uuid.UUID] = Field(default_factory=list)
    skill_ids: List[uuid.UUID] = Field(default_factory=list)


class ModuleManageUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=255)
    description: Optional[str] = Field(default=None, min_length=5)
    difficulty: Optional[str] = Field(default=None, max_length=50)
    duration_minutes: Optional[int] = Field(default=None, ge=1, le=10000)
    order_index: Optional[int] = Field(default=None, ge=1)
    is_published: Optional[bool] = None
    job_role_ids: Optional[List[uuid.UUID]] = None
    skill_ids: Optional[List[uuid.UUID]] = None


class LessonManageCreate(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    content: str = Field(min_length=5)
    duration_minutes: int = Field(default=15, ge=1, le=10000)
    order_index: int = Field(default=1, ge=1)


class TopicExploreRequest(BaseModel):
    broad_topic: str = Field(min_length=2, max_length=150)
    subtopic_count: int = Field(default=4, ge=3, le=6)


class TopicResourceLink(BaseModel):
    title: str
    url: str
    source: str
    resource_type: str  # "blog" | "course" | "video"
    metadata: Optional[str] = None


class TopicSubtopicItem(BaseModel):
    order_index: int
    title: str
    summary: str
    estimated_minutes: int
    key_concepts: List[str] = Field(default_factory=list)
    blogs: List[TopicResourceLink] = Field(default_factory=list)
    courses: List[TopicResourceLink] = Field(default_factory=list)
    videos: List[TopicResourceLink] = Field(default_factory=list)


class TopicExploreResponse(BaseModel):
    broad_topic: str
    target_role: str
    overview: str
    ai_generated: bool = False
    subtopics: List[TopicSubtopicItem] = Field(default_factory=list)
