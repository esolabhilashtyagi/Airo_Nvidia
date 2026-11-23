"""
Agent 7: Question Classification Agent.
Classifies questions into 16 standard technical domains, difficulty ratings,
job roles, and interview rounds.
"""

from typing import Dict, Any
from core.workflow_state import workflow_state, AgentStatus
from models.model_manager import get_model_manager


class QuestionClassificationAgent:
    def __init__(self):
        self.name = "QuestionClassificationAgent"
        workflow_state.register_agent(self.name, agent_type="CLASSIFIER")
        self.model_manager = get_model_manager()

    async def classify_question(self, question_text: str) -> Dict[str, str]:
        workflow_state.update_agent_status(self.name, AgentStatus.RUNNING, current_task="Classifying question topic & difficulty")
        res = await self.model_manager.classify(question_text)
        workflow_state.update_agent_status(self.name, AgentStatus.COMPLETED)
        return res
