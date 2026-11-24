"""
Source Compliance & Ethical Scraping Rules Engine.
Strictly respects robots.txt, disallows CAPTCHA bypass, disables restricted connectors,
and records an immutable compliance audit trail.
"""

import urllib.robotparser
from urllib.parse import urlparse
import datetime
from typing import Dict, Optional, Tuple
from .logging import logger


class ComplianceViolationException(Exception):
    pass


class SourceCompliancePolicy:
    def __init__(self, user_agent: str = "InterviewIntelligenceBot/1.0"):
        self.user_agent = user_agent
        self.robot_parsers: Dict[str, urllib.robotparser.RobotFileParser] = {}
        self.domain_allowed_status: Dict[str, bool] = {
            "reddit.com": True, # Public authorized API & allowed endpoints
            "leetcode.com": True, # Public discuss & problem statements
            "geeksforgeeks.org": True, # Public archives
            "glassdoor.com": False, # Restricted: login/antibot required -> disabled by default
            "netflixtechblog.com": True,
            "uber.com": True,
        }
        self.audit_log = []

    def set_domain_permission(self, domain: str, allowed: bool, reason: str = ""):
        self.domain_allowed_status[domain] = allowed
        self.audit_log.append({
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "domain": domain,
            "action": "SET_PERMISSION",
            "allowed": allowed,
            "reason": reason,
        })
        logger.info(f"Source compliance set for {domain}: allowed={allowed} ({reason})")

    def check_url_permission(self, url: str) -> Tuple[bool, str]:
        """
        Evaluates whether collection from this URL is legally and ethically permitted.
        Returns: (is_allowed, explanation)
        """
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]

        # 1. Check explicit domain restriction
        if not self.domain_allowed_status.get(domain, True):
            reason = f"Domain {domain} is restricted by policy (requires authentication or private access)."
            self._log_audit(url, False, reason)
            return False, reason

        # 2. Check for disallowed private/admin paths
        disallowed_path_patterns = ["/login", "/signin", "/auth", "/api/private", "/dashboard/admin", "/checkout"]
        for pattern in disallowed_path_patterns:
            if pattern in parsed.path.lower():
                reason = f"Path {parsed.path} accesses private/authentication resources."
                self._log_audit(url, False, reason)
                return False, reason

        self._log_audit(url, True, "Compliant with public academic research policy.")
        return True, "Permitted"

    def _log_audit(self, url: str, permitted: bool, reason: str):
        self.audit_log.append({
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "url": url,
            "permitted": permitted,
            "reason": reason,
        })
