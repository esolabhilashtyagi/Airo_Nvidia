import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.interview import InterviewStatus


class InterviewSetupRequest(BaseModel):
    industry_id: Optional[uuid.UUID] = None
    job_role: str = Field(min_length=2)
    target_company: Optional[str] = None
    interview_round: str = "Technical"
    interview_type: str = Field(default="complete", min_length=2, max_length=50)
    difficulty: str = "Intermediate"
    experience_level: str = "Mid-Level"
    duration_minutes: int = Field(default=15, ge=5, le=60)
    number_of_questions: int = Field(default=5, ge=1, le=20)
    mode: str = Field(default="text", pattern="^(text|voice)$")


class InterviewSessionResponse(BaseModel):
    id: uuid.UUID
    job_role: str
    target_company: Optional[str] = None
    interview_round: str
    difficulty: str
    mode: str
    status: InterviewStatus
    started_at: Optional[datetime] = None
    current_question_index: int = 1
    total_questions: int = 5
    interviewer_message: Optional[str] = None
    current_question_id: Optional[uuid.UUID] = None
    history: List[Dict[str, Any]] = Field(default_factory=list)
    ai_status: str = "unavailable"

    model_config = ConfigDict(from_attributes=True)


class InterviewRespondRequest(BaseModel):
    candidate_answer: str = Field(min_length=1, max_length=20000)
    duration_seconds: int = Field(default=0, ge=0, le=7200)


class InterviewResponseReview(BaseModel):
    question_number: int
    question: str
    candidate_answer: str
    refined_answer: Optional[str] = None


class InterviewReportResponse(BaseModel):
    id: uuid.UUID
    mock_interview_id: uuid.UUID
    overall_score: Optional[float] = None
    technical_score: Optional[float] = None
    domain_score: Optional[float] = None
    communication_score: Optional[float] = None
    structure_score: Optional[float] = None
    evaluation_status: str = "unavailable"
    evaluation_provenance: str = "none"
    key_strengths: List[str] = Field(default_factory=list)
    improvement_areas: List[str] = Field(default_factory=list)
    detailed_feedback: Dict[str, Any] = Field(default_factory=dict)
    question_evaluations: List[Dict[str, Any]] = Field(default_factory=list)
    responses: List[InterviewResponseReview] = Field(default_factory=list)
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
