import asyncio
import logging
import time
from typing import Optional, Type
from google import genai
from google.genai import types
from pydantic import BaseModel

from app.core.config import settings
from app.integrations.ai.base import AIProvider, AIResponse
from app.integrations.ai.response_validator import ResponseValidator
from app.integrations.ai.usage_tracker import usage_tracker

logger = logging.getLogger("aairo.ai.gemini")


_JSON_SCHEMA_LIMIT_KEYS = {"minItems", "maxItems", "minimum", "maximum", "minLength", "maxLength"}


def _gemini_response_schema(schema: Type[BaseModel]) -> dict:
    """Build a smaller provider schema; Pydantic still enforces all limits locally."""
    def strip_bounds(value):
        if isinstance(value, dict):
            return {
                key: strip_bounds(item)
                for key, item in value.items()
                if key not in _JSON_SCHEMA_LIMIT_KEYS
            }
        if isinstance(value, list):
            return [strip_bounds(item) for item in value]
        return value

    return strip_bounds(schema.model_json_schema())


class GeminiProvider(AIProvider):
    provider_name = "Google Gemini"

    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY.strip() if settings.GEMINI_API_KEY else ""
        self.model_name = settings.GEMINI_MODEL
        self.timeout = settings.AI_REQUEST_TIMEOUT_SECONDS
        self.max_retries = settings.AI_MAX_RETRIES
        self._client: Optional[genai.Client] = None
        
        if self.api_key:
            try:
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error("Failed to initialize Google GenAI client (%s)", type(e).__name__)

    def is_available(self) -> bool:
        return bool(self.api_key and self._client is not None)

    def _generation_config(
        self,
        system_instruction: Optional[str],
        temperature: float,
        max_tokens: int,
        response_schema: Optional[Type[BaseModel]] = None,
    ) -> types.GenerateContentConfig:
        config = {
            "max_output_tokens": max_tokens,
            "system_instruction": system_instruction,
        }
        if self.model_name.startswith(("gemini-3", "gemini-4")):
            # Gemini 3+ uses thinking controls. Keep model-default sampling and cap
            # reasoning to low for interactive latency and predictable output budget.
            config["thinking_config"] = types.ThinkingConfig(thinking_level="low")
        else:
            config["temperature"] = temperature
        if response_schema is not None:
            config["response_mime_type"] = "application/json"
            # Array/numeric bounds multiply structured-output grammar complexity.
            # Keep those constraints in Pydantic validation, not the provider's
            # generation schema, so the API accepts the request consistently.
            config["response_json_schema"] = _gemini_response_schema(response_schema)
        return types.GenerateContentConfig(**config)

    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2048,
        response_schema: Optional[Type[BaseModel]] = None,
    ) -> AIResponse:
        if not self.is_available():
            return AIResponse(
                is_success=False,
                error_message="Gemini API is not configured. Set GEMINI_API_KEY in environment variables.",
                provider_name="gemini",
                model_name=self.model_name
            )

        start_time = time.time()
        last_error = None

        config = self._generation_config(system_instruction, temperature, max_tokens, response_schema)

        for attempt in range(self.max_retries + 1):
            try:
                # Run synchronous client call in async executor with explicit timeout
                loop = asyncio.get_running_loop()
                response = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: self._client.models.generate_content(
                            model=self.model_name,
                            contents=prompt,
                            config=config
                        )
                    ),
                    timeout=self.timeout
                )

                latency = (time.time() - start_time) * 1000
                prompt_tokens = response.usage_metadata.prompt_token_count if response.usage_metadata else len(prompt) // 4
                comp_tokens = response.usage_metadata.candidates_token_count if response.usage_metadata else len(response.text or "") // 4
                usage = usage_tracker.record_usage(self.model_name, prompt_tokens, comp_tokens)

                if not (response.text or "").strip():
                    finish_reasons = [
                        str(candidate.finish_reason)
                        for candidate in (response.candidates or [])
                        if candidate.finish_reason
                    ]
                    reason = ", ".join(finish_reasons) or "empty response"
                    return AIResponse(
                        is_success=False,
                        error_message=f"Gemini returned no text content ({reason})",
                        provider_name="gemini",
                        model_name=self.model_name,
                        latency_ms=latency,
                        usage=usage,
                    )

                return AIResponse(
                    raw_text=response.text,
                    usage=usage,
                    is_success=True,
                    provider_name="gemini",
                    model_name=self.model_name,
                    latency_ms=latency
                )
            except asyncio.TimeoutError:
                last_error = f"Gemini API request timed out after {self.timeout}s"
                logger.warning(f"Attempt {attempt + 1}: {last_error}")
            except Exception as e:
                # SDK errors may contain request metadata; avoid logging API keys,
                # prompt text, or provider payloads.
                error_code = getattr(e, "code", None)
                error_status = getattr(e, "status", None)
                if error_code is not None:
                    last_error = f"HTTP {error_code} ({error_status or type(e).__name__})"
                else:
                    last_error = type(e).__name__
                logger.warning("Gemini attempt %d failed (%s)", attempt + 1, last_error)
                if isinstance(error_code, int) and 400 <= error_code < 500 and error_code not in (408, 429):
                    break
                if attempt < self.max_retries:
                    await asyncio.sleep(1)

        return AIResponse(
            is_success=False,
            error_message=f"Gemini API request failed after {self.max_retries + 1} attempts: {last_error}",
            provider_name="gemini",
            model_name=self.model_name,
            latency_ms=(time.time() - start_time) * 1000
        )

    async def generate_structured(
        self,
        prompt: str,
        response_schema: Type[BaseModel],
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
    ) -> AIResponse:
        if not self.is_available():
            return AIResponse(
                is_success=False,
                error_message="Gemini API is not configured. Set GEMINI_API_KEY in environment variables.",
                provider_name="gemini",
                model_name=self.model_name
            )

        # Enhance system instruction to enforce JSON matching schema
        json_instruction = (system_instruction or "") + "\nYou MUST return only valid, complete JSON without markdown markdown formatting."

        response = await self.generate_text(
            prompt=prompt,
            system_instruction=json_instruction,
            temperature=temperature,
            max_tokens=4096,
            response_schema=response_schema,
        )

        if not response.is_success or not response.raw_text:
            return response

        validated_model, err = ResponseValidator.validate_pydantic(response.raw_text, response_schema)
        if err or not validated_model:
            logger.error("Structured Gemini response failed schema validation")
            return AIResponse(
                raw_text=response.raw_text,
                is_success=False,
                error_message=f"Failed to parse structured response: {err}",
                provider_name="gemini",
                model_name=self.model_name,
                latency_ms=response.latency_ms,
                usage=response.usage
            )

        response.structured_data = validated_model.model_dump()
        return response
