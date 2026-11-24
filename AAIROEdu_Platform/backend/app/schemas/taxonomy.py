import uuid
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class JobRoleBrief(BaseModel):
    id: uuid.UUID
    industry_id: uuid.UUID
    title: str
    description: Optional[str] = None
    experience_level: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class JobRoleResponse(JobRoleBrief):
    pass


class IndustryCategoryResponse(BaseModel):
    id: uuid.UUID
    industry_id: uuid.UUID
    name: str
    description: Optional[str] = None
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class IndustryBrief(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    description: Optional[str] = None
    icon: Optional[str] = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class IndustryResponse(IndustryBrief):
    categories: List[IndustryCategoryResponse] = []
    job_roles: List[JobRoleResponse] = []

    model_config = ConfigDict(from_attributes=True)


class SkillResponse(BaseModel):
    id: uuid.UUID
    name: str
    category: Optional[str] = None
    is_technical: bool
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class CompanyResponse(BaseModel):
    id: uuid.UUID
    name: str
    industry: Optional[str] = None
    logo_url: Optional[str] = None
    website: Optional[str] = None
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class SubjectResponse(BaseModel):
    id: uuid.UUID
    industry_id: uuid.UUID
    name: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class TopicResponse(BaseModel):
    id: uuid.UUID
    subject_id: uuid.UUID
    name: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class ExperienceLevelResponse(BaseModel):
    id: uuid.UUID
    name: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class InterviewRoundResponse(BaseModel):
    id: uuid.UUID
    industry_id: uuid.UUID
    name: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
