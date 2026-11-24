"""
Agent 13: Quality Assurance Agent.
Validates extracted document structures, schema conformity, missing metadata,
and generates automated data quality metrics.
"""

from typing import Dict, Any, List
from core.workflow_state import workflow_state, AgentStatus
from core.logging import logger


class QualityAssuranceAgent:
    def __init__(self):
        self.name = "QualityAssuranceAgent"
        workflow_state.register_agent(self.name, agent_type="VALIDATOR")

    def validate_raw_document(self, doc: Dict[str, Any]) -> bool:
        workflow_state.update_agent_status(self.name, AgentStatus.RUNNING, current_task="Validating raw document schema")
        required_keys = ["source_platform", "original_url", "raw_text"]
        for key in required_keys:
            if key not in doc or not doc[key]:
                logger.warning(f"[{self.name}] Document validation failed: missing key '{key}'")
                workflow_state.update_agent_status(self.name, AgentStatus.FAILED, failed=True)
                return False

        if len(doc["raw_text"].strip()) < 20:
            logger.warning(f"[{self.name}] Document text too short ({len(doc['raw_text'])} chars)")
            workflow_state.update_agent_status(self.name, AgentStatus.FAILED, failed=True)
            return False

        workflow_state.update_agent_status(self.name, AgentStatus.COMPLETED)
        return True

    def validate_extracted_question(self, question_data: Dict[str, Any]) -> bool:
        if not question_data.get("question_text") or len(question_data["question_text"].strip()) < 10:
            return False
        if not question_data.get("company_name"):
            return False
        return True
