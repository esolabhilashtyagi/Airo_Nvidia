"""NVIDIA NIM / self-hosted OpenAI-compatible chat completions provider."""

import asyncio
import json
import logging
import time
from typing import Optional, Type
from urllib.parse import urlsplit

import httpx
from pydantic import BaseModel

from app.core.config import normalize_nvidia_base_url, settings
from app.integrations.ai.base import AIProvider, AIResponse
from app.integrations.ai.response_validator import ResponseValidator
from app.integrations.ai.usage_tracker import usage_tracker

logger = logging.getLogger("aairo.ai.nvidia")


class NvidiaProvider(AIProvider):
    provider_name = "NVIDIA Nemotron"

    def __init__(self):
        self.api_key = settings.NVIDIA_API_KEY.strip()
        self.model_name = settings.NVIDIA_MODEL.strip()
        self.base_url = normalize_nvidia_base_url(settings.NVIDIA_BASE_URL)
        self.structured_output_mode = settings.NVIDIA_STRUCTURED_OUTPUT_MODE
        # One wall-clock budget covers all requests, retries, and backoff.
        self.timeout = settings.AI_REQUEST_TIMEOUT_SECONDS
        self.max_retries = settings.AI_MAX_RETRIES

    def is_available(self) -> bool:
        # Hostname matching prevents alternate case, ports, or paths bypassing
        # the hosted key requirement. Explicit self-hosted endpoints may omit it.
        hosted_url = urlsplit(self.base_url).hostname == "integrate.api.nvidia.com"
        return bool(self.model_name and self.base_url and (self.api_key or not hosted_url))

    async def _generate(
        self,
        prompt: str,
        system_instruction: Optional[str],
        temperature: float,
        max_tokens: int,
        response_schema: Optional[Type[BaseModel]] = None,
    ) -> AIResponse:
        if not self.is_available():
            return AIResponse(
                is_success=False,
                error_message="NVIDIA inference is not configured. Set NVIDIA_API_KEY or configure a self-hosted NVIDIA_BASE_URL.",
                provider_name="nvidia",
                model_name=self.model_name,
            )

        system_text = system_instruction or ""
        if response_schema is not None:
            system_text += (
                "\nReturn only one complete JSON object matching this JSON Schema. "
                "Do not include markdown or additional text.\n"
                + json.dumps(response_schema.model_json_schema(), ensure_ascii=False)
            )
        messages = []
        if system_text.strip():
            messages.append({"role": "system", "content": system_text})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        if response_schema is not None and self.structured_output_mode == "json_object":
            payload["response_format"] = {"type": "json_object"}

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        started = time.monotonic()
        last_error = "unknown provider error"
        attempts = 0
        try:
            async with asyncio.timeout(self.timeout):
                for attempt in range(self.max_retries + 1):
                    attempts += 1
                    try:
                        async with httpx.AsyncClient(timeout=self.timeout) as client:
                            response = await client.post(
                                f"{self.base_url}/chat/completions",
                                headers=headers,
                                json=payload,
                            )
                        if response.status_code >= 400:
                            last_error = f"HTTP {response.status_code}"
                            logger.warning("NVIDIA request failed (%s)", last_error)
                            if response.status_code not in (408, 429) and response.status_code < 500:
                                break
                            if attempt < self.max_retries:
                                await asyncio.sleep(min(2 ** attempt, 4))
                            continue

                        data = response.json()
                        choices = data.get("choices") or []
                        choice = choices[0] if choices else {}
                        message = choice.get("message") or {}
                        content = message.get("content")
                        finish_reason = str(choice.get("finish_reason") or "")
                        if finish_reason in ("length", "content_filter", "refusal") or "refusal" in finish_reason:
                            last_error = f"Rejected completion (finish_reason={finish_reason})"
                            break

                        has_refusal = bool(message.get("refusal")) or (
                            isinstance(content, list)
                            and any(isinstance(p, dict) and p.get("type") == "refusal" for p in content)
                        )
                        if has_refusal:
                            last_error = "NVIDIA explicitly refused the request"
                            break

                        if isinstance(content, list):
                            content = "".join(
                                part.get("text", "") for part in content if isinstance(part, dict)
                            )
                        if not isinstance(content, str) or not content.strip():
                            last_error = "NVIDIA returned an empty response"
                            break

                        usage_data = data.get("usage") or {}
                        prompt_tokens = int(usage_data.get("prompt_tokens") or 0)
                        completion_tokens = int(usage_data.get("completion_tokens") or 0)
                        usage = usage_tracker.record_usage(
                            self.model_name, prompt_tokens, completion_tokens
                        )
                        return AIResponse(
                            raw_text=content,
                            usage=usage,
                            provider_name="nvidia",
                            model_name=self.model_name,
                            latency_ms=(time.monotonic() - started) * 1000,
                        )
                    except (httpx.TimeoutException, httpx.TransportError) as exc:
                        last_error = type(exc).__name__
                        logger.warning("NVIDIA request transport failed (%s)", last_error)
                        if attempt < self.max_retries:
                            await asyncio.sleep(min(2 ** attempt, 4))
                    except (ValueError, TypeError, KeyError) as exc:
                        # Do not log the provider body: it may echo candidate data.
                        last_error = type(exc).__name__
                        logger.warning("NVIDIA returned an invalid response (%s)", last_error)
                        break
                    except Exception as exc:
                        last_error = type(exc).__name__
                        logger.warning("NVIDIA request failed (%s)", last_error)
                        break
        except TimeoutError:
            last_error = "Overall request timeout exceeded"
            logger.warning("NVIDIA overall request timeout exceeded")

        return AIResponse(
            is_success=False,
            error_message=f"NVIDIA inference failed after {attempts} attempt(s): {last_error}",
            provider_name="nvidia",
            model_name=self.model_name,
            latency_ms=(time.monotonic() - started) * 1000,
        )

    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> AIResponse:
        return await self._generate(prompt, system_instruction, temperature, max_tokens)

    async def generate_structured(
        self,
        prompt: str,
        response_schema: Type[BaseModel],
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
    ) -> AIResponse:
        response = await self._generate(
            prompt, system_instruction, temperature, 4096, response_schema
        )
        if not response.is_success or not response.raw_text:
            return response
        validated, error = ResponseValidator.validate_pydantic(
            response.raw_text, response_schema
        )
        if error or validated is None:
            return AIResponse(
                raw_text=response.raw_text,
                is_success=False,
                error_message=f"Structured NVIDIA response failed validation: {error}",
                provider_name="nvidia",
                model_name=self.model_name,
                latency_ms=response.latency_ms,
                usage=response.usage,
            )
        response.structured_data = validated.model_dump()
        return response
