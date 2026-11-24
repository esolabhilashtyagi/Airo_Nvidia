"""
Agent 7: Question Classification Agent.
Classifies questions into canonical technical domains, difficulty ratings,
job roles, and interview rounds.
Guarantees strict conformance to canonical categories, preventing the '* Domain' bug.
"""

from typing import Dict, Any
from core.workflow_state import workflow_state, AgentStatus
from models.model_manager import get_model_manager
from models.fallback_models import CANONICAL_CATEGORIES, FallbackNLPModel


class QuestionClassificationAgent:
    def __init__(self):
        self.name = "QuestionClassificationAgent"
        workflow_state.register_agent(self.name, agent_type="CLASSIFIER")
        self.model_manager = get_model_manager()
        self.nlp = FallbackNLPModel()

    async def classify_question(self, question_text: str) -> Dict[str, str]:
        workflow_state.update_agent_status(self.name, AgentStatus.RUNNING, current_task="Classifying question topic & difficulty")
        try:
            res = await self.model_manager.classify(question_text)
        except Exception:
            res = self.nlp.classify_question(question_text)

        # Enforce canonical category constraint
        raw_cat = res.get("category", "")
        if not raw_cat or "Domain" in raw_cat or raw_cat not in CANONICAL_CATEGORIES:
            fallback_res = self.nlp.classify_question(question_text)
            res["category"] = fallback_res["category"]
            if not res.get("difficulty") or res.get("difficulty") not in ["Easy", "Medium", "Hard"]:
                res["difficulty"] = fallback_res["difficulty"]

        workflow_state.update_agent_status(self.name, AgentStatus.COMPLETED)
        return res
