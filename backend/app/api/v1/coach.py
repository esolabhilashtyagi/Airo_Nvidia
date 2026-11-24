import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_candidate_profile
from app.core.database import get_async_db
from app.models.candidate import CandidateProfile
from app.schemas.coach import CoachChatRequest, CoachChatResponse, CoachConversationResponse, SkillGapResponse
from app.schemas.common import APIResponse
from app.schemas.module import RoadmapResponse
from app.services.coach_service import CoachService
from app.services.learning_resources import LearningResourceService

router = APIRouter(prefix="/coach", tags=["AI Career Coach"])


@router.get("/skill-gap", response_model=APIResponse[SkillGapResponse])
async def get_skill_gap(
    candidate_profile: CandidateProfile = Depends(get_current_candidate_profile),
    db: AsyncSession = Depends(get_async_db)
):
    analysis = await CoachService.get_skill_gap_analysis(db, candidate_profile)
    return APIResponse(data=analysis, message="Skill gap analysis completed")


@router.post("/roadmap/generate", response_model=APIResponse[RoadmapResponse])
async def generate_roadmap(
    candidate_profile: CandidateProfile = Depends(get_current_candidate_profile),
    db: AsyncSession = Depends(get_async_db)
):
    roadmap = await CoachService.generate_personalized_roadmap(db, candidate_profile)
    return APIResponse(data=roadmap, message="Personalized roadmap generated")


@router.post("/chat", response_model=APIResponse[CoachChatResponse])
async def chat_with_coach(
    request: CoachChatRequest,
    candidate_profile: CandidateProfile = Depends(get_current_candidate_profile),
    db: AsyncSession = Depends(get_async_db)
):
    reply = await CoachService.chat_with_coach(db, candidate_profile, request)
    return APIResponse(data=reply, message="Coach response status returned")


@router.get("/resources", response_model=APIResponse[dict])
async def learning_resources(
    topic: str = Query(min_length=2, max_length=200),
    target_role: str | None = Query(default=None, min_length=2, max_length=255),
    recent_years: int | None = Query(default=None, ge=1, le=10),
    candidate_profile: CandidateProfile = Depends(get_current_candidate_profile),
):
    role = (target_role or candidate_profile.target_role or "").strip()
    if not role:
        raise HTTPException(status_code=422, detail="Choose a target role to tailor learning resources.")
    if len(topic.strip()) < 2:
        raise HTTPException(status_code=422, detail="Enter a learning topic with at least two nonblank characters.")
    resources = await LearningResourceService.search(topic.strip(), role, limit=5, recent_years=recent_years)
    return APIResponse(data=resources, message="Learning resource search completed")


@router.get("/conversations", response_model=APIResponse[list[CoachConversationResponse]])
async def list_conversations(
    candidate_profile: CandidateProfile = Depends(get_current_candidate_profile),
    db: AsyncSession = Depends(get_async_db),
):
    conversations = await CoachService.list_conversations(db, candidate_profile.id)
    return APIResponse(data=conversations, message="Coach conversations retrieved")


@router.get("/conversations/{conversation_id}", response_model=APIResponse[CoachConversationResponse])
async def get_conversation(
    conversation_id: uuid.UUID,
    candidate_profile: CandidateProfile = Depends(get_current_candidate_profile),
    db: AsyncSession = Depends(get_async_db),
):
    conversation = await CoachService.get_conversation(db, candidate_profile.id, conversation_id)
    return APIResponse(data=conversation, message="Coach conversation retrieved")
