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
        """Verifies whether the local Ollama runtime is reachable with sub-second fail-fast timeout."""
        try:
            fast_timeout = httpx.Timeout(0.3, connect=0.3)
            resp = await self.client.get(f"{self.base_url}/api/tags", timeout=fast_timeout)
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

    async def generate_structural_followups(
        self, base_question: str, company: str = "Technology Firm", role: str = "Software Engineer"
    ) -> List[Dict[str, Any]]:
        """
        Synthesizes 2 structurally distinct follow-up questions from a base interview question.
        Ensures strict structural differentiation (concurrency, distributed consensus, fault-tolerance)
        rather than superficial combinatorial number-swapping.
        Returns entries marked with source_type='ai_followup'.
        """
        schema = (
            "[\n"
            "  {\n"
            "    \"variant_type\": \"Distributed Scale & Concurrency Variant\",\n"
            "    \"question_text\": \"Full in-depth question with distributed or concurrency constraints\",\n"
            "    \"category\": \"Distributed Systems\",\n"
            "    \"difficulty\": \"Hard\",\n"
            "    \"skills_tested\": [\"Distributed Systems\", \"Concurrency\"],\n"
            "    \"source_type\": \"ai_followup\"\n"
            "  },\n"
            "  {\n"
            "    \"variant_type\": \"Fault Tolerance & Boundary Resilience\",\n"
            "    \"question_text\": \"Full in-depth question with failover or partition resilience constraints\",\n"
            "    \"category\": \"System Design\",\n"
            "    \"difficulty\": \"Hard\",\n"
            "    \"skills_tested\": [\"Fault Tolerance\", \"Resilience\"],\n"
            "    \"source_type\": \"ai_followup\"\n"
            "  }\n"
            "]"
        )
        task = (
            f"Given the following base interview question asked at {company} for the role of {role}:\n\n"
            f"Base Question: \"{base_question}\"\n\n"
            "Generate exactly 2 structurally distinct follow-up interview questions.\n"
            "RULES:\n"
            "1. DO NOT simply change scale numbers (e.g., swapping 100 to 5,000 requests is strictly forbidden).\n"
            "2. Variant 1 must introduce a major distributed systems or high-concurrency constraint (e.g. partition tolerance, lock-free structures, disk spillover memory bounds, or multi-datacenter consensus).\n"
            "3. Variant 2 must introduce a resilience, failover, or hard algorithmic boundary condition (e.g. Byzantine failure mitigation, zero-data-loss crash recovery, dynamic schema evolution, or p99 tail latency bounding).\n"
            "4. Both items must have \"source_type\": \"ai_followup\"."
        )

        try:
            if await self.is_available():
                extracted = await self.extract_structured_json(task, schema)
                if isinstance(extracted, list) and len(extracted) >= 2:
                    clean_res = []
                    for item in extracted[:2]:
                        if isinstance(item, dict) and item.get("question_text"):
                            item["source_type"] = "ai_followup"
                            if not item.get("difficulty"):
                                item["difficulty"] = "Hard"
                            clean_res.append(item)
                    if len(clean_res) == 2:
                        return clean_res
        except Exception as e:
            logger.debug(f"Nemotron follow-up generation failed, using structural fallback: {e}")

        # Deterministic structural fallback engine
        is_design = any(k in base_question.lower() for k in ["design", "architecture", "scale", "system", "service", "cluster"])
        if is_design:
            v1_text = (
                f"Active-Active Geo-Replication Follow-up for {company}: How would you extend this system "
                f"across 3 active-active cloud regions with sub-20ms p99 write latency? Specifically address "
                f"conflict-free replicated data types (CRDTs), partition tolerance under cross-region fiber cuts, "
                f"and cross-region read-after-write causal consistency."
            )
            v2_text = (
                f"Chaos Resilience & Graceful Degradation Follow-up for {company}: During a major dependency outage "
                f"where 35% of downstream services fail or experience 5-second timeouts, how does your architecture "
                f"enforce circuit breaking, tenant-level token bucket shedding, and asynchronous reconciliation "
                f"to ensure zero data loss and prevent cascading system-wide collapse?"
            )
            cat1 = "Distributed Systems"
            cat2 = "System Design"
            skills1 = ["Geo-Replication", "CRDTs", "Causal Consistency"]
            skills2 = ["Circuit Breakers", "Chaos Engineering", "Resilience"]
        else:
            v1_text = (
                f"Distributed In-Memory Partitioning Follow-up for {company}: How would you adapt this algorithmic "
                f"solution if the input data stream exceeds single-node RAM by 100x and must be partitioned across "
                f"a cluster of 32 worker nodes? Formulate the data partitioning strategy (consistent hashing) and "
                f"distributed state synchronization protocol to minimize network shuffling."
            )
            v2_text = (
                f"Lock-Free Concurrency & Memory Safety Follow-up for {company}: Re-implement this solution for a "
                f"multi-threaded environment with 128 hardware threads contending concurrently. Eliminate global mutex locks "
                f"using atomic compare-and-swap (CAS) primitives and analyze memory ordering (acquire-release semantics) "
                f"to prevent race conditions, false sharing, and ABA anomalies."
            )
            cat1 = "Concurrency & Multi-Threading"
            cat2 = "Data Structures & Algorithms"
            skills1 = ["Distributed Partitioning", "Consistent Hashing", "Shuffling"]
            skills2 = ["Lock-Free Concurrency", "Atomic CAS", "Memory Barriers"]

        return [
            {
                "variant_type": "Distributed Scale & Concurrency Variant",
                "question_text": v1_text,
                "category": cat1,
                "difficulty": "Hard",
                "skills_tested": skills1,
                "source_type": "ai_followup",
            },
            {
                "variant_type": "Fault Tolerance & Boundary Resilience",
                "question_text": v2_text,
                "category": cat2,
                "difficulty": "Hard",
                "skills_tested": skills2,
                "source_type": "ai_followup",
            },
        ]
