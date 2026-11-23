"""
Glassdoor & Restricted Platform Ethical Connector.
Strictly respects automated collection policies.
When public access is restricted by robots.txt or login requirements, this connector
marks the source as compliance-restricted and does not attempt bypasses or evasion.
"""

from typing import List, Dict, Any
from .base_collector import BaseCollector
from core.permissions import ComplianceViolationException
from core.logging import logger


class GlassdoorCollector(BaseCollector):
    def __init__(self, **kwargs):
        super().__init__(
            source_name="Glassdoor",
            base_url="https://www.glassdoor.com/Interview",
            **kwargs,
        )

    async def collect(self, limit: int = 5, use_mock: bool = False) -> List[Dict[str, Any]]:
        # Check compliance status: Glassdoor explicitly disallows unauthorized scrapers
        permitted, reason = self.compliance_policy.check_url_permission(self.base_url)
        if not permitted:
            logger.info(
                f"Glassdoor automated collection disabled ethically: {reason}. "
                "Returning zero records as required by ethical compliance rules."
            )
            return []

        # If authorized API keys were configured, permitted retrieval would run here
        return []
