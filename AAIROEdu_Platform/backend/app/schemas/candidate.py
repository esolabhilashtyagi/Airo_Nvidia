import uuid
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.schemas.taxonomy import CompanyResponse, IndustryResponse


class EducationCreate(BaseModel):
    degree: str
    field_of_study: str
    institution: str
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    grade: Optional[str] = None
    is_current: bool = False


class EducationResponse(EducationCreate):
    id: uuid.UUID
    candidate_profile_id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)


class ExperienceCreate(BaseModel):
    company_name: str
    job_title: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_current: bool = False
    description: Optional[str] = None


class ExperienceResponse(ExperienceCreate):
    id: uuid.UUID
    candidate_profile_id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)


class TargetCompanyCreate(BaseModel):
    company_name: str
    target_role: Optional[str] = None


class TargetCompanyResponse(BaseModel):
    id: uuid.UUID
    candidate_profile_id: uuid.UUID
    company_id: uuid.UUID
    target_role: Optional[str] = None
    company: Optional[CompanyResponse] = None

    model_config = ConfigDict(from_attributes=True)


class OnboardingStepRequest(BaseModel):
    step: int = Field(ge=1, le=7)
    candidate_type: Optional[str] = None
    sub_category: Optional[str] = None
    industry_id: Optional[uuid.UUID] = None
    current_company: Optional[str] = None
    current_role: Optional[str] = None
    target_role: Optional[str] = None
    total_experience_months: Optional[int] = None
    relevant_experience_months: Optional[int] = None
    employment_status: Optional[str] = None
    key_skills: Optional[List[str]] = None
    career_goals: Optional[str] = None
    education: Optional[List[EducationCreate]] = None
    experience: Optional[List[ExperienceCreate]] = None
    interview_rounds_preferred: Optional[List[str]] = None
    target_companies: Optional[List[TargetCompanyCreate]] = None
    interaction_preference: Optional[str] = None # text or voice
    is_final_step: bool = False

    @field_validator("industry_id", mode="before")
    @classmethod
    def blank_industry_is_unset(cls, value):
        # Older clients may submit an empty HTML-select value before the
        # industry step. Treat it as omitted instead of rejecting the request
        # as an invalid UUID.
        if isinstance(value, str) and not value.strip():
            return None
        return value


class CandidateProfileResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    candidate_type: Optional[str] = None
    sub_category: Optional[str] = None
    industry_id: Optional[uuid.UUID] = None
    industry: Optional[IndustryResponse] = None
    current_company: Optional[str] = None
    current_role: Optional[str] = None
    target_role: Optional[str] = None
    total_experience_months: int = 0
    relevant_experience_months: int = 0
    employment_status: Optional[str] = None
    key_skills: List[str] = []
    career_goals: Optional[str] = None
    onboarding_completed: bool = False
    onboarding_step: int = 1
    interview_rounds_preferred: List[str] = []
    interaction_preference: str = "text"
    interview_readiness_score: float = 0.0
    education_history: List[EducationResponse] = []
    experience_history: List[ExperienceResponse] = []
    target_companies: List[TargetCompanyResponse] = []

    model_config = ConfigDict(from_attributes=True)
