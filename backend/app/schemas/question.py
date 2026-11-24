import uuid
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.models.question import ApprovalStatus, DifficultyLevel, QuestionType, SourceProvenance
from app.schemas.taxonomy import IndustryBrief, JobRoleBrief, CompanyResponse, SkillResponse


class QuestionOption(BaseModel):
    id: str
    text: str
    is_correct: Optional[bool] = None


class QuestionCreate(BaseModel):
    question_text: str = Field(min_length=10, max_length=10000)
    question_type: QuestionType
    industry_id: uuid.UUID
    job_role_id: Optional[uuid.UUID] = None
    subject: str = Field(min_length=1, max_length=255)
    topic: str = Field(min_length=1, max_length=255)
    difficulty: DifficultyLevel = DifficultyLevel.INTERMEDIATE
    interview_round: str = "Technical"
    options: List[QuestionOption] = Field(default_factory=list)
    expected_answer: Optional[str] = Field(default=None, max_length=20000)
    explanation: Optional[str] = None
    evaluation_rubric: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    source_provenance: SourceProvenance
    industry_category_id: Optional[uuid.UUID] = None
    job_role_ids: List[uuid.UUID] = Field(default_factory=list)
    skill_ids: List[uuid.UUID] = Field(default_factory=list)
    company_ids: List[uuid.UUID] = Field(default_factory=list)
    subject_id: Optional[uuid.UUID] = None
    topic_id: Optional[uuid.UUID] = None
    experience_level: Optional[str] = Field(default=None, max_length=100)
    experience_level_id: Optional[uuid.UUID] = None
    interview_round_id: Optional[uuid.UUID] = None
    source_url: Optional[str] = Field(default=None, max_length=2000)
    marks: Optional[float] = Field(default=None, gt=0, le=1000)
    estimated_minutes: Optional[int] = Field(default=None, gt=0, le=600)
    approval_status: ApprovalStatus = ApprovalStatus.PENDING
    workflow_status: Literal["draft", "pending_review"] = "pending_review"

    @model_validator(mode="after")
    def validate_question_shape(self):
        if self.question_type in (QuestionType.MCQ_SINGLE, QuestionType.MCQ_MULTIPLE):
            if len(self.options) < 2:
                raise ValueError("Choice questions require at least two options")
            option_ids = [option.id.strip().upper() for option in self.options]
            correct_count = sum(option.is_correct is True for option in self.options)
            if len(set(option_ids)) != len(option_ids) or not all(option_ids):
                raise ValueError("Choice option IDs must be non-empty and unique")
            if correct_count < 1 or (self.question_type == QuestionType.MCQ_SINGLE and correct_count != 1):
                raise ValueError("Choice questions require valid correct option(s)")
        elif self.options:
            raise ValueError("Only multiple-choice questions may contain options")
        if self.topic_id and not self.subject_id:
            raise ValueError("A topic must be linked through its subject")
        if len(set(self.job_role_ids)) != len(self.job_role_ids) or len(set(self.skill_ids)) != len(self.skill_ids) or len(set(self.company_ids)) != len(self.company_ids):
            raise ValueError("Taxonomy associations must be unique")
        return self


class QuestionDraftRequest(BaseModel):
    industry_id: uuid.UUID
    question_type: QuestionType
    subject: str = Field(min_length=1, max_length=255)
    topic: str = Field(min_length=1, max_length=255)
    difficulty: DifficultyLevel = DifficultyLevel.INTERMEDIATE
    interview_round: str = Field(default="Technical", max_length=100)
    job_role_id: Optional[uuid.UUID] = None
    job_role_ids: List[uuid.UUID] = Field(default_factory=list)
    industry_category_id: Optional[uuid.UUID] = None
    skill_ids: List[uuid.UUID] = Field(default_factory=list)
    company_ids: List[uuid.UUID] = Field(default_factory=list)
    subject_id: Optional[uuid.UUID] = None
    topic_id: Optional[uuid.UUID] = None
    experience_level: Optional[str] = Field(default=None, max_length=100)
    experience_level_id: Optional[uuid.UUID] = None
    interview_round_id: Optional[uuid.UUID] = None
    source_url: Optional[str] = Field(default=None, max_length=2000)
    marks: Optional[float] = Field(default=None, gt=0, le=1000)
    estimated_minutes: Optional[int] = Field(default=None, gt=0, le=600)


class QuestionUpdate(BaseModel):
    question_text: Optional[str] = None
    question_type: Optional[QuestionType] = None
    industry_id: Optional[uuid.UUID] = None
    job_role_id: Optional[uuid.UUID] = None
    subject: Optional[str] = None
    topic: Optional[str] = None
    difficulty: Optional[DifficultyLevel] = None
    interview_round: Optional[str] = None
    options: Optional[List[QuestionOption]] = None
    expected_answer: Optional[str] = Field(default=None, max_length=20000)
    explanation: Optional[str] = None
    evaluation_rubric: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    source_provenance: Optional[SourceProvenance] = None
    approval_status: Optional[ApprovalStatus] = None
    industry_category_id: Optional[uuid.UUID] = None
    job_role_ids: Optional[List[uuid.UUID]] = None
    skill_ids: Optional[List[uuid.UUID]] = None
    company_ids: Optional[List[uuid.UUID]] = None
    subject_id: Optional[uuid.UUID] = None
    topic_id: Optional[uuid.UUID] = None
    experience_level: Optional[str] = Field(default=None, max_length=100)
    experience_level_id: Optional[uuid.UUID] = None
    interview_round_id: Optional[uuid.UUID] = None
    source_url: Optional[str] = Field(default=None, max_length=2000)
    marks: Optional[float] = Field(default=None, gt=0, le=1000)
    estimated_minutes: Optional[int] = Field(default=None, gt=0, le=600)


class QuestionResponse(BaseModel):
    id: uuid.UUID
    question_text: str
    question_type: QuestionType
    industry_id: uuid.UUID
    job_role_id: Optional[uuid.UUID] = None
    subject: str
    topic: str
    difficulty: DifficultyLevel
    interview_round: str
    options: List[Dict[str, Any]] = Field(default_factory=list)
    expected_answer: Optional[str] = None
    explanation: Optional[str] = None
    evaluation_rubric: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    source_provenance: SourceProvenance
    approval_status: ApprovalStatus
    is_bookmarked: bool = False
    created_at: datetime
    updated_at: datetime
    industry: Optional[IndustryBrief] = None
    job_role: Optional[JobRoleBrief] = None
    industry_category_id: Optional[uuid.UUID] = None
    subject_id: Optional[uuid.UUID] = None
    topic_id: Optional[uuid.UUID] = None
    experience_level: Optional[str] = None
    experience_level_id: Optional[uuid.UUID] = None
    interview_round_id: Optional[uuid.UUID] = None
    source_url: Optional[str] = None
    marks: Optional[float] = None
    estimated_minutes: Optional[int] = None
    job_roles: List[JobRoleBrief] = Field(default_factory=list)
    skills: List[SkillResponse] = Field(default_factory=list)
    companies: List[CompanyResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ManagedQuestionResponse(QuestionResponse):
    workflow_status: str = "pending_review"
    version_number: int = 1
    root_question_id: Optional[uuid.UUID] = None
    created_by_id: Optional[uuid.UUID] = None
    reviewed_by_id: Optional[uuid.UUID] = None
    reviewed_at: Optional[datetime] = None
    review_comment: Optional[str] = None
    published_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None


class CandidateQuestionResponse(BaseModel):
    id: uuid.UUID
    question_text: str
    question_type: QuestionType
    industry_id: uuid.UUID
    job_role_id: Optional[uuid.UUID] = None
    job_role_ids: List[uuid.UUID] = Field(default_factory=list)
    skill_ids: List[uuid.UUID] = Field(default_factory=list)
    company_ids: List[uuid.UUID] = Field(default_factory=list)
    industry_category_id: Optional[uuid.UUID] = None
    subject_id: Optional[uuid.UUID] = None
    topic_id: Optional[uuid.UUID] = None
    subject: str
    topic: str
    experience_level: Optional[str] = None
    experience_level_id: Optional[uuid.UUID] = None
    interview_round: str
    interview_round_id: Optional[uuid.UUID] = None
    difficulty: DifficultyLevel
    options: List[Dict[str, Any]] = Field(default_factory=list)
    # Keep these compatibility keys present while guaranteeing candidate-safe null values.
    expected_answer: None = None
    explanation: None = None
    source_provenance: SourceProvenance
    marks: Optional[float] = None
    estimated_minutes: Optional[int] = None
    is_bookmarked: bool = False
    industry: Optional[IndustryBrief] = None
    job_roles: List[JobRoleBrief] = Field(default_factory=list)
    skills: List[SkillResponse] = Field(default_factory=list)
    companies: List[CompanyResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PracticeHistoryItem(BaseModel):
    id: uuid.UUID
    question_id: uuid.UUID
    question_text: str
    question_type: QuestionType
    user_response: str
    is_correct: Optional[bool] = None
    score_percentage: Optional[float] = None
    evaluation_status: str
    evaluation_provenance: str
    feedback: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QuestionPracticeRequest(BaseModel):
    user_response: str = Field(min_length=1, max_length=20000)


class QuestionPracticeResponse(BaseModel):
    question_id: uuid.UUID
    is_correct: Optional[bool] = None
    score_percentage: Optional[float] = None
    evaluation_status: str
    evaluation_provenance: str
    expected_answer: Optional[str] = None
    explanation: Optional[str] = None
    feedback: str
