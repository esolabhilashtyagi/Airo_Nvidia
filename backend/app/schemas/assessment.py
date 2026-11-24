import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.models.assessment import AttemptStatus
from app.schemas.question import QuestionResponse


class AssessmentConfigureRequest(BaseModel):
    industry_id: uuid.UUID
    job_role_id: Optional[uuid.UUID] = None
    subject: Optional[str] = Field(default=None, max_length=255, description="Optional subject filter for assessment questions")
    topic: Optional[str] = Field(default=None, max_length=255, description="Optional topic filter for assessment questions")
    topics: List[str] = Field(default_factory=list, max_length=20, description="Additional topic filters (optional)")
    skill_id: Optional[uuid.UUID] = None
    question_types: List[str] = Field(default_factory=list, max_length=12)
    difficulty: Optional[str] = None
    interview_round: Optional[str] = None
    num_questions: int = Field(default=5, ge=1, le=50)
    duration_minutes: int = Field(default=20, ge=5, le=180)
    marks_per_question: int = Field(default=10, gt=0, le=100)
    negative_marking_points: int = Field(default=0, ge=0, le=100)
    randomize_questions: bool = True

    @field_validator("subject", "topic", mode="before")
    @classmethod
    def normalize_blank_taxonomy(cls, value):
        if isinstance(value, str):
            return value.strip() or None
        return value

    @field_validator("topics", mode="before")
    @classmethod
    def normalize_topics(cls, value):
        if value is None:
            return []
        if not isinstance(value, list):
            return value
        normalized = []
        seen = set()
        for item in value:
            if not isinstance(item, str):
                normalized.append(item)
                continue
            topic = item.strip()
            if len(topic) > 255:
                raise ValueError("Topic labels must not exceed 255 characters")
            if topic and topic.casefold() not in seen:
                normalized.append(topic)
                seen.add(topic.casefold())
        return normalized


class AssessmentResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str] = None
    industry_id: uuid.UUID
    job_role_id: Optional[uuid.UUID] = None
    difficulty: str
    duration_minutes: int
    total_questions: int
    passing_percentage: float
    marks_per_question: float = 10.0
    negative_marking_points: float = 0.0
    randomize_questions: bool = True
    ai_generated_question_count: int = Field(default=0, ge=0, le=50)

    model_config = ConfigDict(from_attributes=True)


class AssessmentStartResponse(BaseModel):
    attempt_id: uuid.UUID
    assessment_id: uuid.UUID
    title: str
    duration_minutes: int
    total_questions: int
    started_at: datetime
    ends_at: datetime
    questions: List[QuestionResponse]
    saved_answers: List[Dict[str, Any]] = Field(default_factory=list)


class CandidateAnswerSaveRequest(BaseModel):
    question_id: uuid.UUID
    selected_options: List[str] = Field(default_factory=list, max_length=100)
    text_response: Optional[str] = Field(default=None, max_length=50000)
    is_marked_for_review: bool = False

    @field_validator("selected_options")
    @classmethod
    def validate_option_ids(cls, values):
        normalized = [value.strip() for value in values]
        if any(not value or len(value) > 255 for value in normalized):
            raise ValueError("Selected option IDs must contain 1-255 characters")
        if len({value.casefold() for value in normalized}) != len(normalized):
            raise ValueError("Selected option IDs must not repeat")
        return normalized

    @field_validator("text_response")
    @classmethod
    def normalize_blank_answer(cls, value):
        # Preserve indentation and trailing newlines in nonblank code answers.
        return value if value and value.strip() else None

    @model_validator(mode="after")
    def validate_answer_shape(self):
        if self.selected_options and self.text_response is not None:
            raise ValueError("Submit selected options or a text response, not both")
        return self


class AssessmentResultResponse(BaseModel):
    id: uuid.UUID
    assessment_attempt_id: uuid.UUID
    total_score: float
    max_score: float
    percentage: Optional[float] = None
    passed: Optional[bool] = None
    correct_count: int
    incorrect_count: int
    unanswered_count: int
    topic_breakdown: Dict[str, Any] = {}
    difficulty_breakdown: Dict[str, Any] = {}
    strong_areas: List[str] = []
    weak_areas: List[str] = []
    recommendations: Optional[str] = None
    evaluation_status: str = "unavailable"
    evaluation_provenance: str = "none"
    question_feedback: List[Dict[str, Any]] = Field(default_factory=list)
    time_spent_seconds: int = 0
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AttemptHistoryItem(BaseModel):
    id: uuid.UUID
    assessment_id: uuid.UUID
    assessment_title: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: AttemptStatus
    percentage: Optional[float] = None
    passed: Optional[bool] = None
    evaluation_status: str = "unavailable"

    model_config = ConfigDict(from_attributes=True)
