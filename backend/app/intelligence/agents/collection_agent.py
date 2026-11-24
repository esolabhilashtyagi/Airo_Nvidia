"""
Agent 4: Web Collection Agent.
Collects authorized public webpage content using async connectors with exponential backoff,
saves raw text, timestamps, and source URLs.
"""

from typing import List, Dict, Any
from core.workflow_state import workflow_state, AgentStatus
from core.logging import logger
from collectors import (
    RedditCollector,
    LeetCodeCollector,
    GFGCollector,
    GlassdoorCollector,
    CompanyBlogCollector,
)


class WebCollectionAgent:
    def __init__(self):
        self.name = "WebCollectionAgent"
        workflow_state.register_agent(self.name, agent_type="IO_SERVICE")
        self.collectors = {
            "reddit": RedditCollector(),
            "leetcode": LeetCodeCollector(),
            "gfg": GFGCollector(),
            "glassdoor": GlassdoorCollector(),
            "company_blog": CompanyBlogCollector(),
        }

    async def collect_content(self, collector_type: str, limit: int = 5, use_mock: bool = True) -> List[Dict[str, Any]]:
        workflow_state.update_agent_status(self.name, AgentStatus.RUNNING, current_task=f"Collecting from {collector_type}")
        collector = self.collectors.get(collector_type.lower())
        if not collector:
            logger.warning(f"[{self.name}] Unknown collector type '{collector_type}'")
            workflow_state.update_agent_status(self.name, AgentStatus.COMPLETED)
            return []

        try:
            records = await collector.collect(limit=limit, use_mock=use_mock)
            logger.info(f"[{self.name}] Successfully collected {len(records)} items via {collector_type}")
            workflow_state.update_agent_status(self.name, AgentStatus.COMPLETED)
            return records
        except Exception as e:
            logger.error(f"[{self.name}] Collection failed for {collector_type}: {e}")
            workflow_state.update_agent_status(self.name, AgentStatus.FAILED, failed=True)
            return []
