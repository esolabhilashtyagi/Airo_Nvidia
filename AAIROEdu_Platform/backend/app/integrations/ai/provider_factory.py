import logging
from typing import Optional
from app.integrations.ai.base import AIProvider
from app.integrations.ai.gemini_provider import GeminiProvider
from app.integrations.ai.nvidia_provider import NvidiaProvider
from app.core.config import settings

logger = logging.getLogger("aairo.ai.factory")

_cached_provider: Optional[AIProvider] = None


def get_ai_provider() -> AIProvider:
    """Return the configured AI provider; never silently switch providers."""
    global _cached_provider
    if _cached_provider is None:
        provider_name = settings.AI_PROVIDER.strip().lower()
        if provider_name == "nvidia":
            _cached_provider = NvidiaProvider()
        elif provider_name == "gemini":
            _cached_provider = GeminiProvider()
        else:
            raise ValueError("AI_PROVIDER must be either 'nvidia' or 'gemini'")
        if _cached_provider.is_available():
            logger.info("AI provider initialized: %s (active)", _cached_provider.provider_name)
        else:
            logger.warning("AI provider %s is selected but not configured", provider_name)
            
    return _cached_provider
