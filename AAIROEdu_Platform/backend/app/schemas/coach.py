import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.coach import MessageSender


class LearningPriorityItem(BaseModel):
    priority: int
    skill_or_topic: str
    actionable_recommendation: str
    estimated_hours: int


class SkillGapResponse(BaseModel):
    strong_skills: List[str] = Field(default_factory=list)
    weak_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    technical_gaps: List[str] = Field(default_factory=list)
    domain_gaps: List[str] = Field(default_factory=list)
    self_reported_skills: List[str] = Field(default_factory=list)
    skill_evidence: Dict[str, str] = Field(default_factory=dict)
    evidence_sources: List[str] = Field(default_factory=list)
    learning_priorities: List[LearningPriorityItem] = Field(default_factory=list)
    coach_summary: str
    ai_status: str = "unavailable"


class CoachChatRequest(BaseModel):
    conversation_id: Optional[uuid.UUID] = None
    message: str = Field(min_length=1, max_length=10000)


class CoachMessageResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    sender: MessageSender
    message_text: str
    metadata_payload: Dict[str, Any] = {}
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CoachConversationResponse(BaseModel):
    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[CoachMessageResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class CoachChatResponse(BaseModel):
    conversation_id: uuid.UUID
    reply: Optional[str] = None
    suggested_actions: List[str] = Field(default_factory=list)
    ai_status: str = "unavailable"
