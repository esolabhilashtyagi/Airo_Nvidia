from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: Optional[float] = None


class AIResponse(BaseModel):
    model_config = {"protected_namespaces": ()}
    raw_text: Optional[str] = None
    structured_data: Optional[Dict[str, Any]] = None
    usage: TokenUsage = TokenUsage()
    is_success: bool = True
    error_message: Optional[str] = None
    provider_name: str = "unknown"
    model_name: str = "unknown"
    latency_ms: float = 0.0


class AIProvider(ABC):
    provider_name: str = "unknown"
    model_name: str = "unknown"

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> AIResponse:
        """Generate unstructured or formatted text response."""
        pass

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        response_schema: Type[BaseModel],
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
    ) -> AIResponse:
        """Generate structured response validated against a Pydantic schema."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if provider API credentials are configured and active."""
        pass
