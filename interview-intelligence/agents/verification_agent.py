"""
Agent 8: Authenticity Verification Agent.
Evaluates first-person experiential markers, flags generic educational tutorials or suspicious claims,
and assigns confidence scores. Questionable records are flagged for human review.
"""

from typing import Dict, Any
from core.workflow_state import workflow_state, AgentStatus
from models.model_manager import get_model_manager


class AuthenticityVerificationAgent:
    def __init__(self):
        self.name = "AuthenticityVerificationAgent"
        workflow_state.register_agent(self.name, agent_type="VERIFIER")
        self.model_manager = get_model_manager()

    async def verify_record(self, raw_text: str) -> Dict[str, Any]:
        workflow_state.update_agent_status(self.name, AgentStatus.RUNNING, current_task="Evaluating authenticity and provenance")
        verification = await self.model_manager.verify(raw_text)
        
        # Determine human review status
        if verification.get("confidence_score", 0.0) < 0.70:
            verification["review_status"] = "NEEDS_MANUAL_REVIEW"
        else:
            verification["review_status"] = "AUTOMATICALLY_VERIFIED"

        workflow_state.update_agent_status(self.name, AgentStatus.COMPLETED)
        return verification
