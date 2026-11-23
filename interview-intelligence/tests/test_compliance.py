"""
Source Compliance tests: Verify robots.txt enforcement, rate limits, and zero-bypass ethics.
"""

import pytest
from core.permissions import SourceCompliancePolicy
from core.rate_limiter import RateLimiter, CircuitBreakerOpenException


def test_compliance_policy_restrictions():
    policy = SourceCompliancePolicy()

    # Public sources permitted
    allowed, _ = policy.check_url_permission("https://www.reddit.com/r/cscareerquestions")
    assert allowed is True

    allowed_lc, _ = policy.check_url_permission("https://leetcode.com/discuss/interview-question/12345")
    assert allowed_lc is True

    # Restricted sources blocked
    blocked_gd, reason_gd = policy.check_url_permission("https://www.glassdoor.com/Interview/index.htm")
    assert blocked_gd is False
    assert "restricted by policy" in reason_gd

    # Private endpoints blocked
    blocked_login, reason_login = policy.check_url_permission("https://example.com/login/user")
    assert blocked_login is False
    assert "private" in reason_login


@pytest.mark.asyncio
async def test_rate_limiter_and_circuit_breaker():
    limiter = RateLimiter(default_rps=5.0, max_burst=2)
    # Token acquire should succeed
    await limiter.acquire("example.com")
    assert "example.com" in limiter.domain_tokens

    # Trip circuit breaker
    limiter.record_failure("example.com", status_code=429, retry_after=2.0)
    with pytest.raises(CircuitBreakerOpenException):
        await limiter.acquire("example.com")
