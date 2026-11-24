"""
Agent 2: Source Discovery Agent.
Discovers interview experiences, public company blogs, and coding problem sources.
Maintains the active source registry and manages unlimited multi-engine open-web discovery.
"""

from typing import List, Dict, Any
from core.workflow_state import workflow_state, AgentStatus
from core.logging import logger
from database.repository import get_db_repository
from collectors.open_web_collector import OpenWebCollector


class SourceDiscoveryAgent:
    def __init__(self):
        self.name = "SourceDiscoveryAgent"
        workflow_state.register_agent(self.name, agent_type="MULTI_ENGINE_DISCOVERY")
        self.db = get_db_repository()
        self.open_collector = OpenWebCollector()

    async def discover_sources(self, target: str = "all") -> List[Dict[str, Any]]:
        workflow_state.update_agent_status(self.name, AgentStatus.RUNNING, current_task=f"Discovering sources for {target}")

        all_sources = [
            {"name": "Open Web (SearXNG / Multi-Engine)", "collector_type": "open_web", "url": "http://localhost:8080/search"},
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

    async def generate_dynamic_dorks(
        self,
        company: str,
        role: str,
        yoe: float = 3.0,
        skills: List[str] = None,
    ) -> Dict[str, Any]:
        """Generates dynamic open-web search queries using Nemotron instead of static dorks."""
        from models.model_manager import get_model_manager
        mm = get_model_manager()
        return await mm.generate_domain_dorks(company=company, role=role, yoe=yoe, skills=skills)

    async def discover_candidate_urls(
        self,
        company: str,
        role: str,
        page: int = 1,
        yoe: float = 3.0,
        skills: List[str] = None,
        round_number: int = None,
    ) -> List[str]:
        """Discovers full candidate interview post URLs across open web using dynamic Nemotron dorks."""
        import httpx
        async with httpx.AsyncClient(headers=self.open_collector.headers, timeout=10.0) as client:
            return await self.open_collector.discover_urls(
                client, company, role, page=page, yoe=yoe, skills=skills, round_number=round_number
            )
