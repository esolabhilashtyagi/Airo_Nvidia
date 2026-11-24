import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.resume import SuggestionStatus


class ResumeSuggestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    resume_analysis_id: uuid.UUID
    category: str
    original_text: Optional[str] = None
    suggested_text: str
    reason: Optional[str] = None
    supporting_context: Optional[str] = None
    status: SuggestionStatus


class ResumeAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    resume_id: uuid.UUID
    status: str
    overall_score: float
    category_scores: Dict[str, float]
    completeness_score: float
    skills_relevance_score: float
    experience_quality_score: float
    target_role_alignment_score: float
    formatting_score: float
    strengths: List[str]
    weaknesses: List[str]
    summary_analysis: Optional[str] = None
    missing_keywords: List[str]
    improvement_opportunities: List[str]
    extraction_confidence: float
    analysis_provider: Optional[str] = None
    suggestions: List[ResumeSuggestionResponse]
    created_at: datetime


class ResumeVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    resume_id: uuid.UUID
    version_number: int
    content: Dict[str, Any]
    change_summary: Optional[str] = None
    created_at: datetime


class ResumeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    candidate_profile_id: uuid.UUID
    file_name: str
    file_size_bytes: int
    mime_type: str
    parsing_status: str
    analysis_status: str
    extraction_confidence: float
    extraction_error: Optional[str] = None
    analysis_error: Optional[str] = None
    parsed_data: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    latest_analysis: Optional[ResumeAnalysisResponse] = None


class ResumeDetailResponse(ResumeResponse):
    raw_text: Optional[str] = None
    versions: List[ResumeVersionResponse] = Field(default_factory=list)


class ResumeParsedDataUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    parsed_data: Dict[str, Any]


class SuggestionActionRequest(BaseModel):
    action: str = Field(pattern="^(accept|reject)$")
    edited_text: Optional[str] = Field(default=None, max_length=20000)


class ResumeATSReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    job_title: str = Field(min_length=2, max_length=200)
    job_description: str = Field(min_length=80, max_length=12000)


class ResumeATSReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    resume_id: uuid.UUID
    job_title: str
    ats_score: float
    keyword_match_score: float
    section_match_score: float
    matched_keywords: List[str]
    missing_keywords: List[str]
    matched_sections: List[str]
    missing_sections: List[str]
    formatting_warnings: List[str]
    created_at: datetime
