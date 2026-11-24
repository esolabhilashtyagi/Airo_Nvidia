"""
Agent 3: Source Compliance Agent.
Enforces website robots.txt rules, respects rate-limits, checks permission statuses,
disables restricted connectors, and logs compliance audits. Never bypasses restrictions.
"""

from typing import Tuple
from core.workflow_state import workflow_state, AgentStatus
from core.permissions import SourceCompliancePolicy
from core.logging import logger


class SourceComplianceAgent:
    def __init__(self):
        self.name = "SourceComplianceAgent"
        workflow_state.register_agent(self.name, agent_type="DETERMINISTIC")
        self.policy = SourceCompliancePolicy()

    async def verify_compliance(self, url: str, source_name: str) -> Tuple[bool, str]:
        workflow_state.update_agent_status(self.name, AgentStatus.RUNNING, current_task=f"Auditing {source_name}")
        permitted, reason = self.policy.check_url_permission(url)
        if permitted:
            logger.info(f"[{self.name}] Compliance verified for {source_name} ({url})")
        else:
            logger.warning(f"[{self.name}] Compliance rejection for {source_name}: {reason}")
        
        workflow_state.update_agent_status(self.name, AgentStatus.COMPLETED)
        return permitted, reason
