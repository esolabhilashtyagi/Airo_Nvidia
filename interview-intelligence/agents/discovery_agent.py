"""
Agent 2: Source Discovery Agent.
Discovers interview experiences, public company blogs, and coding problem sources.
Maintains the active source registry and prioritizes authorized public endpoints.
"""

from typing import List, Dict, Any
from core.workflow_state import workflow_state, AgentStatus
from core.logging import logger
from database.repository import get_db_repository


class SourceDiscoveryAgent:
    def __init__(self):
        self.name = "SourceDiscoveryAgent"
        workflow_state.register_agent(self.name, agent_type="DETERMINISTIC")
        self.db = get_db_repository()

    async def discover_sources(self, target: str = "all") -> List[Dict[str, Any]]:
        workflow_state.update_agent_status(self.name, AgentStatus.RUNNING, current_task=f"Discovering sources for {target}")
        
        all_sources = [
            {"name": "Reddit", "collector_type": "reddit", "url": "https://www.reddit.com/r/cscareerquestions"},
            {"name": "LeetCode", "collector_type": "leetcode", "url": "https://leetcode.com/discuss/interview-question"},
            {"name": "GeeksforGeeks", "collector_type": "gfg", "url": "https://www.geeksforgeeks.org/interview-experiences"},
            {"name": "Engineering Blogs", "collector_type": "company_blog", "url": "https://netflixtechblog.com"},
            {"name": "Glassdoor", "collector_type": "glassdoor", "url": "https://www.glassdoor.com/Interview"},
        ]

        if target != "all":
            selected = [s for s in all_sources if s["collector_type"] == target.lower() or s["name"].lower() == target.lower()]
        else:
            selected = all_sources

        logger.info(f"[{self.name}] Discovered {len(selected)} sources matching filter '{target}'")
        workflow_state.update_agent_status(self.name, AgentStatus.COMPLETED)
        return selected
