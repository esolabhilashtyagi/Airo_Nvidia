"""
Local NVIDIA Nemotron Client.
Interfaces with local inference runtimes (e.g., Ollama or local OpenAI-compatible endpoints)
running NVIDIA Nemotron open-weight models (nemotron-mini:latest, nemotron-4-340b, etc.)
with zero paid API dependencies.
"""

import httpx
import json
from typing import Dict, Any, Optional, List
from core.config import settings
from core.logging import logger


class NemotronLocalClient:
    def __init__(self, base_url: Optional[str] = None, model_name: Optional[str] = None):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model_name = model_name or settings.PRIMARY_MODEL
        self.client = httpx.AsyncClient(timeout=30.0)

    async def is_available(self) -> bool:
        """Verifies whether the local Ollama runtime is reachable."""
        try:
            resp = await self.client.get(f"{self.base_url}/api/tags", timeout=0.8)
            return resp.status_code == 200
        except Exception:
            return False

    async def generate_completion(
        self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.1
    ) -> Optional[str]:
        """
        Sends prompt to local Nemotron inference engine.
        Returns generated text or None if local model is offline.
        """
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "top_p": 0.9,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            response = await self.client.post(f"{self.base_url}/api/generate", json=payload)
            if response.status_code == 200:
                data = response.json()
                return data.get("response", "").strip()
            else:
                logger.warning(f"Local model inference returned HTTP {response.status_code}: {response.text}")
                return None
        except Exception as e:
            logger.debug(f"Local Ollama inference unreachable at {self.base_url}: {e}")
            return None

    async def extract_structured_json(
        self, prompt: str, schema_description: str
    ) -> Optional[Dict[str, Any]]:
        """
        Prompts Nemotron to produce strictly valid JSON matching schema_description.
        """
        system = (
            "You are an expert technical extraction system. "
            "You MUST respond ONLY with valid JSON conforming to the requested schema. "
            "Do not output markdown code blocks, explanations, or commentary."
        )
        full_prompt = f"Schema:\n{schema_description}\n\nTask:\n{prompt}\n\nJSON output:"
        raw_text = await self.generate_completion(full_prompt, system_prompt=system, temperature=0.0)
        if not raw_text:
            return None

        clean_text = raw_text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]

        try:
            return json.loads(clean_text.strip())
        except Exception as e:
            logger.warning(f"Failed to parse Nemotron JSON output: {e}. Raw: {raw_text[:200]}")
            return None
