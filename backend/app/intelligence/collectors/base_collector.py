"""
Base Collector Engine.
Provides asynchronous HTTP fetching, per-domain rate limiting, robots.txt compliance checking,
exponential backoff, circuit breaking, and mock demonstration fallbacks.
"""

import asyncio
import httpx
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional
from datetime import datetime
from urllib.parse import urlparse

from core.config import settings
from core.logging import logger
from core.rate_limiter import RateLimiter, CircuitBreakerOpenException
from core.permissions import SourceCompliancePolicy, ComplianceViolationException


class BaseCollector:
    def __init__(
        self,
        source_name: str,
        base_url: str,
        rate_limiter: Optional[RateLimiter] = None,
        compliance_policy: Optional[SourceCompliancePolicy] = None,
    ):
        self.source_name = source_name
        self.base_url = base_url
        self.rate_limiter = rate_limiter or RateLimiter(default_rps=settings.DEFAULT_REQUEST_DELAY_SEC)
        self.compliance_policy = compliance_policy or SourceCompliancePolicy(user_agent=settings.USER_AGENT)
        self.client = httpx.AsyncClient(
            headers={"User-Agent": settings.USER_AGENT, "Accept": "text/html,application/json"},
            timeout=15.0,
            follow_redirects=True,
        )

    async def fetch_url(self, url: str) -> Optional[str]:
        """
        Safely fetches page content if compliance permits and rate limits allow.
        """
        # 1. Compliance verification
        permitted, reason = self.compliance_policy.check_url_permission(url)
        if not permitted:
            logger.warning(f"Collection blocked by compliance policy for {url}: {reason}")
            raise ComplianceViolationException(reason)

        # 2. Rate limiting & circuit breaking
        domain = urlparse(url).netloc
        try:
            await self.rate_limiter.acquire(domain)
        except CircuitBreakerOpenException as e:
            logger.error(f"Cannot fetch {url}: {e}")
            return None

        # 3. HTTP Request
        try:
            response = await self.client.get(url)
            if response.status_code == 200:
                self.rate_limiter.record_success(domain)
                return response.text
            elif response.status_code == 429:
                retry_after = float(response.headers.get("Retry-After", 10.0))
                self.rate_limiter.record_failure(domain, status_code=429, retry_after=retry_after)
                return None
            else:
                logger.warning(f"HTTP {response.status_code} fetching {url}")
                self.rate_limiter.record_failure(domain, status_code=response.status_code)
                return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            self.rate_limiter.record_failure(domain)
            return None

    def clean_html(self, html_content: str) -> str:
        """Parses HTML and extracts readable text."""
        soup = BeautifulSoup(html_content, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
            tag.decompose()
        return " ".join(soup.get_text().split())

    async def collect(self, limit: int = 5, use_mock: bool = False) -> List[Dict[str, Any]]:
        """Abstract collect method to be implemented by specific collectors."""
        raise NotImplementedError("Subclasses must implement collect()")

    async def close(self):
        await self.client.aclose()
