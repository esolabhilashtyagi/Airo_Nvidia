"""
Model Manager: Orchestrates local inference selection, hardware evaluation,
and automatic fallback chains between NVIDIA Nemotron, Qwen2.5, and deterministic models.
"""

import os
from typing import Dict, Any, Optional
from core.config import settings
from core.logging import logger
from .nemotron_client import NemotronLocalClient
from .fallback_models import FallbackNLPModel
from .embedding_model import LocalEmbeddingModel


class ModelManager:
    def __init__(self):
        self.nemotron = NemotronLocalClient()
        self.fallback = FallbackNLPModel()
        self.embedding = LocalEmbeddingModel(dim=settings.EMBEDDING_DIM)
        self._llm_active: Optional[bool] = None

    async def check_hardware_and_model_status(self) -> Dict[str, Any]:
        """Evaluates CPU, RAM, and detects if local Nemotron runtime is accessible."""
        available_ram_gb = 0.0
        try:
            import ctypes
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ('dwLength', ctypes.c_ulong),
                    ('dwMemoryLoad', ctypes.c_ulong),
                    ('ullTotalPhys', ctypes.c_ulonglong),
                    ('ullAvailPhys', ctypes.c_ulonglong),
                ]
            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            available_ram_gb = stat.ullAvailPhys / (1024**3)
        except Exception:
            available_ram_gb = 4.0

        ollama_reachable = await self.nemotron.is_available()
        self._llm_active = ollama_reachable

        return {
            "primary_model": settings.PRIMARY_MODEL,
            "fallback_model": settings.FALLBACK_MODEL,
            "embedding_model": settings.EMBEDDING_MODEL,
            "ollama_url": settings.OLLAMA_BASE_URL,
            "ollama_online": ollama_reachable,
            "available_ram_gb": round(available_ram_gb, 2),
            "mode": "NVIDIA_NEMOTRON_LOCAL" if ollama_reachable else "ZERO_DEPENDENCY_FALLBACK",
        }

    async def extract_experience(self, text: str, source_url: str = "") -> Dict[str, Any]:
        """Runs Nemotron if reachable, otherwise uses high-precision heuristic fallback."""
        if self._llm_active is None:
            await self.check_hardware_and_model_status()

        if self._llm_active:
            schema = """{
                "company_name": "string",
                "job_role": "string",
                "interview_round": "string",
                "experience_level": "string",
                "questions": ["string"]
            }"""
            prompt = f"Extract company, role, interview round, experience level, and questions asked from this text:\n{text}"
            res = await self.nemotron.extract_structured_json(prompt, schema)
            if res and res.get("questions"):
                return res

        return self.fallback.extract_interview_entities(text, source_url)

    async def classify(self, question_text: str) -> Dict[str, str]:
        """Classifies category and difficulty."""
        if self._llm_active:
            schema = '{"category": "string", "difficulty": "Easy|Medium|Hard"}'
            prompt = f"Classify this interview question into topic and difficulty:\n{question_text}"
            res = await self.nemotron.extract_structured_json(prompt, schema)
            if res and "category" in res and "difficulty" in res:
                return res

        return self.fallback.classify_question(question_text)

    async def verify(self, text: str) -> Dict[str, Any]:
        """Verifies candidate authenticity and confidence score."""
        if self._llm_active:
            schema = '{"is_first_person": bool, "is_suspicious": bool, "confidence_score": float, "flags": ["string"]}'
            prompt = f"Analyze whether this text is an authentic first-person interview experience:\n{text}"
            res = await self.nemotron.extract_structured_json(prompt, schema)
            if res and "confidence_score" in res:
                res["verification_method"] = "NVIDIA_NEMOTRON_LLM"
                return res

        return self.fallback.verify_authenticity(text)

    def generate_embedding(self, text: str) -> list:
        return self.embedding.encode(text)


_model_manager_instance: Optional[ModelManager] = None


def get_model_manager() -> ModelManager:
    global _model_manager_instance
    if _model_manager_instance is None:
        _model_manager_instance = ModelManager()
    return _model_manager_instance
