"""
Pydantic schemas for data validation, serialization, and API request/response contracts.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, HttpUrl, ConfigDict


class CompanyBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    normalized_name: Optional[str] = None
    industry: Optional[str] = None
    website: Optional[str] = None


class CompanyCreate(CompanyBase):
    pass


class CompanyResponse(CompanyBase):
    id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class JobRoleBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    normalized_title: Optional[str] = None
    department: Optional[str] = None
    experience_tier: Optional[str] = None


class JobRoleCreate(JobRoleBase):
    pass


class JobRoleResponse(JobRoleBase):
    id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class CodingProblemBase(BaseModel):
    problem_title: str
    problem_statement: str
    input_format: Optional[str] = None
    output_format: Optional[str] = None
    constraints: Optional[str] = None
    examples_json: Optional[List[Dict[str, Any]]] = None
    programming_languages: Optional[str] = None
    algorithmic_concepts: Optional[str] = None
    source_reference: Optional[str] = None


class CodingProblemCreate(CodingProblemBase):
    question_id: Optional[str] = None


class CodingProblemResponse(CodingProblemBase):
    id: str
    question_id: str
    model_config = ConfigDict(from_attributes=True)


class InterviewQuestionBase(BaseModel):
    company_name: str
    job_role: str
    experience_level: Optional[str] = "Mid"
    interview_round: Optional[str] = "Technical Round"
    question_text: str = Field(..., min_length=5)
    question_category: str = "Data Structures and Algorithms"
    difficulty: str = "Medium"
    source_platform: str
    original_url: str
    publication_date: Optional[datetime] = None
    verification_status: str = "UNVERIFIED"
    confidence_score: float = 0.0
    content_hash: Optional[str] = None


class InterviewQuestionCreate(InterviewQuestionBase):
    experience_id: Optional[str] = None
    round_id: Optional[str] = None
    coding_problem: Optional[CodingProblemBase] = None


class InterviewQuestionResponse(InterviewQuestionBase):
    id: str
    collection_timestamp: datetime
    coding_problem: Optional[CodingProblemResponse] = None
    model_config = ConfigDict(from_attributes=True)


class InterviewExperienceBase(BaseModel):
    company_name: str
    job_role: str
    candidate_experience_level: Optional[str] = None
    offer_status: Optional[str] = None
    difficulty_rating: Optional[str] = None
    overall_feedback: Optional[str] = None
    source_platform: str
    original_url: str
    publication_date: Optional[datetime] = None


class InterviewExperienceCreate(InterviewExperienceBase):
    questions: List[InterviewQuestionCreate] = []


class InterviewExperienceResponse(InterviewExperienceBase):
    id: str
    collected_at: datetime
    content_hash: str
    questions: List[InterviewQuestionResponse] = []
    model_config = ConfigDict(from_attributes=True)


class DataSourceBase(BaseModel):
    name: str
    base_url: str
    collector_type: str
    is_active: bool = True


class DataSourceCreate(DataSourceBase):
    can_collect: bool = True
    rate_limit_rps: float = 1.0
    robots_txt_url: Optional[str] = None


class DataSourceResponse(DataSourceBase):
    id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ExtractionJobCreate(BaseModel):
    source_name: str
    max_items: int = 10


class ExtractionJobResponse(BaseModel):
    id: str
    source_name: str
    status: str
    items_collected: int
    items_extracted: int
    error_message: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]
    model_config = ConfigDict(from_attributes=True)


class QuestionSearchQuery(BaseModel):
    query: Optional[str] = None
    company: Optional[str] = None
    role: Optional[str] = None
    category: Optional[str] = None
    difficulty: Optional[str] = None
    verified_only: bool = False
    limit: int = 20
    offset: int = 0


class InterviewBlueprintRequest(BaseModel):
    company_name: Optional[str] = Field(None, description="Established company name (Case A) or None for Startup")
    industry: Optional[str] = Field(None, description="Industry domain for Startups (Case B: Fintech, AI/GenAI, E-Commerce, SaaS, etc.)")
    role: Optional[str] = Field("All Roles", description="Target job role (optional, defaults to 'All Roles' for company-wide questions)")
    years_of_experience: float = Field(3.0, ge=0.0, le=30.0, description="Years of experience (YoE)")
    skills: List[str] = Field(default=[], description="List of technical skills e.g. ['Python', 'PostgreSQL', 'Kafka']")
    difficulty: Optional[str] = Field(None, description="Optional difficulty preference: Easy, Medium, Hard")


class RoundDetail(BaseModel):
    round_number: int
    round_name: str
    round_type: str
    focus_areas: List[str]
    questions: List[Dict[str, Any]]


class InterviewBlueprintResponse(BaseModel):
    target_type: str # ESTABLISHED_COMPANY or STARTUP_INDUSTRY
    target_name: str
    industry: Optional[str]
    role: str
    role_family: Optional[str] = "TECH"
    years_of_experience: float
    yoe_tier: str
    matched_skills: List[str]
    total_rounds: int
    rounds: List[RoundDetail]
    preparation_strategy: str


class AnalyticsSummary(BaseModel):
    total_experiences: int
    total_questions: int
    total_companies: int
    verified_questions: int
    unverified_questions: int
    category_distribution: Dict[str, int]
    difficulty_distribution: Dict[str, int]
    platform_distribution: Dict[str, int]
    company_distribution: Dict[str, int]
