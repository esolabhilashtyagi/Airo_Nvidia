"""
Model Manager: Orchestrates local inference selection, hardware evaluation,
and automatic fallback chains between NVIDIA Nemotron, Qwen2.5, and deterministic models.
"""

import os
from typing import Dict, Any, Optional
from core.config import settings
from core.logging import logger
from .nemotron_client import NemotronLocalClient
from .fallback_models import FallbackNLPModel, CANONICAL_CATEGORIES, strip_question_wrappers
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
        """
        Runs Nemotron with strict data hygiene and hard REJECT escape hatch.
        Rejects blog headlines, HN rants, forum chatter, and generic trivia.
        Falls back to deterministic fallback model if offline.
        """
        if self._llm_active is None:
            await self.check_hardware_and_model_status()

        if self._llm_active:
            schema = """{
                "valid": true,
                "rejection_reason": "none",
                "company_name": "string",
                "job_role": "string",
                "interview_round": "string",
                "experience_level": "string",
                "questions": ["string"]
            }"""
            prompt = (
                "You are an expert technical interview extraction system with strict data hygiene.\n"
                "CRITICAL EXTRACTION & HYGIENE RULES:\n"
                "1. HARD REJECT ESCAPE HATCH: If the text is a blog headline, article title, forum rant/debate, "
                "opinion piece, README table of contents, interview preparation guide, or generic discussion rather "
                "than a concrete technical interview problem, you MUST return {\"valid\": false, \"rejection_reason\": \"not_an_interview_question\", \"questions\": []}.\n"
                "2. NO BOILERPLATE FRAMING: Do NOT add framing prefixes (e.g. 'In an interview for...', 'Company: ...', '[Technical Round X]'). "
                "Do NOT add trailing boilerplate (e.g. 'Discuss architectural trade-offs and edge cases.'). Return ONLY the standalone question.\n"
                "3. ATOMIC QUESTIONS: If the input has multiple rounds or problems, return each atomic question as a separate item. Never output a multi-round summary paragraph.\n"
                "4. STRIP HTML: Strip raw HTML/markdown tags (<summary>, <details>, etc.) completely.\n\n"
                f"Input Text:\n{text}"
            )
            res = await self.nemotron.extract_structured_json(prompt, schema)
            if res:
                if not res.get("valid", True) or res.get("rejection_reason") in ["not_an_interview_question", "noise", "rant", "headline"]:
                    return {"valid": False, "questions": [], "rejection_reason": res.get("rejection_reason", "rejected")}
                raw_qs = res.get("questions", [])
                clean_qs = [strip_question_wrappers(q) for q in raw_qs if len(strip_question_wrappers(q)) >= 20]
                if clean_qs:
                    res["questions"] = clean_qs
                    res["valid"] = True
                    return res
                else:
                    return {"valid": False, "questions": [], "rejection_reason": "no_valid_questions_found"}

        return self.fallback.extract_interview_entities(text, source_url)

    async def classify(self, question_text: str) -> Dict[str, str]:
        """
        Classifies category strictly within canonical whitelist enum and infers difficulty.
        Zero unconstrained categories or '* Domain' bugs.
        """
        if self._llm_active:
            cat_enum = "|".join(CANONICAL_CATEGORIES)
            schema = f'{{"category": "{cat_enum}", "difficulty": "Easy|Medium|Hard"}}'
            prompt = (
                "Classify this technical interview question into EXACTLY ONE canonical category from the list and its difficulty:\n"
                f"Canonical Categories: {', '.join(CANONICAL_CATEGORIES)}\n\n"
                "RULES:\n"
                "- Do NOT invent new categories. Never append 'Domain' to words.\n"
                "- Questions with metric trees, north star, DAU/MAU -> 'Product Management'.\n"
                "- Questions with rate limiters, token buckets, sliding window counters -> 'System Design'.\n"
                "- Questions with thread-safe caches, pub-sub, LLD, machine coding -> 'Object-Oriented Programming'.\n\n"
                f"Question:\n{question_text}"
            )
            res = await self.nemotron.extract_structured_json(prompt, schema)
            if res and res.get("category") in CANONICAL_CATEGORIES and res.get("difficulty") in ["Easy", "Medium", "Hard"]:
                return res

        return self.fallback.classify_question(question_text)

    async def verify(self, text: str) -> Dict[str, Any]:
        """Verifies candidate authenticity and confidence score."""
        if self._llm_active:
            schema = '{"is_first_person": bool, "is_suspicious": bool, "confidence_score": float, "flags": ["string"]}'
            prompt = (
                "Analyze whether this text represents an authentic, real-world technical interview experience:\n"
                "Reject generic tutorials, textbook questions without interview context, or theoretical debates.\n\n"
                f"Text:\n{text}"
            )
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
