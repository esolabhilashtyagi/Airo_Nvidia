"""
Agent 5: Interview Experience Extraction Agent.
Uses local NVIDIA Nemotron model (or high-accuracy heuristic fallback) to extract:
company name, job role, experience level, interview round, questions, and topics.
Distinguishes first-person interview accounts from generic tutorials.
"""

from typing import Dict, Any
from core.workflow_state import workflow_state, AgentStatus
from core.logging import logger
from models.model_manager import get_model_manager


class ExperienceExtractionAgent:
    def __init__(self):
        self.name = "ExperienceExtractionAgent"
        workflow_state.register_agent(self.name, agent_type="LOCAL_AI_AGENT")
        self.model_manager = get_model_manager()

    async def extract_experience(self, text: str, source_url: str = "") -> Dict[str, Any]:
        workflow_state.update_agent_status(self.name, AgentStatus.RUNNING, current_task="Extracting interview experience")
        try:
            result = await self.model_manager.extract_experience(text, source_url)
            workflow_state.update_agent_status(self.name, AgentStatus.COMPLETED)
            return result
        except Exception as e:
            logger.error(f"[{self.name}] Extraction error: {e}")
            workflow_state.update_agent_status(self.name, AgentStatus.FAILED, failed=True)
            return self.model_manager.fallback.extract_interview_entities(text, source_url)
