"""
Asynchronous Rate Limiter, Exponential Backoff, and Circuit Breaker engine.
Ensures zero source overloading, respects Retry-After headers and HTTP 429 backoff.
"""

import asyncio
import time
import math
import random
from typing import Dict, Optional
from .logging import logger


class CircuitBreakerOpenException(Exception):
    pass


class RateLimiter:
    """
    Per-domain token-bucket rate limiter with circuit breaker and backoff.
    """
    def __init__(self, default_rps: float = 1.0, max_burst: int = 5):
        self.default_rps = default_rps
        self.max_burst = max_burst
        self.domain_tokens: Dict[str, float] = {}
        self.domain_last_update: Dict[str, float] = {}
        self.domain_rps: Dict[str, float] = {}
        self.circuit_failures: Dict[str, int] = {}
        self.circuit_open_until: Dict[str, float] = {}
        self._lock = asyncio.Lock()

    def set_domain_limit(self, domain: str, rps: float):
        self.domain_rps[domain] = max(0.1, rps)

    async def acquire(self, domain: str):
        """Waits until a token is available for the given domain."""
        async with self._lock:
            now = time.time()
            # Check circuit breaker
            if domain in self.circuit_open_until:
                cooldown_remaining = self.circuit_open_until[domain] - now
                if cooldown_remaining > 0:
                    logger.warning(
                        f"Circuit breaker OPEN for domain {domain}. Wait {cooldown_remaining:.1f}s"
                    )
                    raise CircuitBreakerOpenException(f"Domain {domain} circuit is tripped.")
                else:
                    # Half-open state
                    del self.circuit_open_until[domain]
                    self.circuit_failures[domain] = 0

            rps = self.domain_rps.get(domain, self.default_rps)
            last = self.domain_last_update.get(domain, now)
            tokens = self.domain_tokens.get(domain, self.max_burst)

            # Refill tokens
            elapsed = now - last
            tokens = min(self.max_burst, tokens + elapsed * rps)
            self.domain_last_update[domain] = now

            if tokens < 1.0:
                sleep_time = (1.0 - tokens) / rps
                self.domain_tokens[domain] = 0.0
            else:
                sleep_time = 0.0
                self.domain_tokens[domain] = tokens - 1.0

        if sleep_time > 0:
            await asyncio.sleep(sleep_time)

    def record_success(self, domain: str):
        if domain in self.circuit_failures:
            self.circuit_failures[domain] = max(0, self.circuit_failures[domain] - 1)

    def record_failure(self, domain: str, status_code: Optional[int] = None, retry_after: Optional[float] = None):
        """Handles HTTP 429, 503, or network errors with exponential backoff / trip."""
        failures = self.circuit_failures.get(domain, 0) + 1
        self.circuit_failures[domain] = failures

        if status_code == 429:
            # Explicit rate limit
            wait_sec = retry_after if retry_after else (2 ** min(failures, 6)) + random.uniform(0.5, 2.0)
            logger.warning(f"HTTP 429 for {domain}! Backing off for {wait_sec:.1f}s")
            self.circuit_open_until[domain] = time.time() + wait_sec
        elif failures >= 5:
            # Trip circuit
            trip_time = 60.0
            logger.error(f"Trip circuit breaker for {domain} after {failures} consecutive errors. Cooling down for {trip_time}s")
            self.circuit_open_until[domain] = time.time() + trip_time
