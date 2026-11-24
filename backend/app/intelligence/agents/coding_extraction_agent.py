"""
Agent 6: Coding Problem & Full Article Extraction Agent (Nemotron Gate).
Extracts atomic technical interview questions from full-length articles (Medium, Substack,
Blind, personal blogs, etc.) extracted via trafilatura.
Gates out opinion pieces, tutorials, and SEO listicles, and decomposes authentic multi-round
interview debriefs into discrete, canonical question records.
"""

import re
import json
from typing import Dict, Any, Optional, List
from core.workflow_state import workflow_state, AgentStatus
from core.logging import logger
from models.nemotron_client import NemotronLocalClient
from models.fallback_models import (
    FallbackNLPModel,
    strip_question_wrappers,
    canonicalize_text,
    get_dedup_hash,
    CANONICAL_CATEGORIES,
)


CANONICAL_ROLES_MAP = {
    "sde": "Software Development Engineer II",
    "sde 1": "Software Development Engineer I",
    "sde 2": "Software Development Engineer II",
    "sde 3": "Senior Software Development Engineer",
    "sde1": "Software Development Engineer I",
    "sde2": "Software Development Engineer II",
    "swe": "Software Development Engineer II",
    "software engineer": "Software Development Engineer II",
    "backend": "Backend Engineer",
    "backend engineer": "Backend Engineer",
    "systems": "Systems Software Engineer",
    "systems engineer": "Systems Software Engineer",
    "ml engineer": "Machine Learning Engineer",
    "ai engineer": "Machine Learning Engineer",
    "pm": "Senior Product Manager",
    "product manager": "Senior Product Manager",
}


class CodingProblemExtractionAgent:
    def __init__(self):
        self.name = "CodingProblemExtractionAgent"
        workflow_state.register_agent(self.name, agent_type="NEMOTRON_EXTRACTION_GATE")
        self.nemotron = NemotronLocalClient()
        self.nlp = FallbackNLPModel()

    def _normalize_role(self, role: str) -> str:
        r_low = (role or "").strip().lower()
        if r_low in CANONICAL_ROLES_MAP:
            return CANONICAL_ROLES_MAP[r_low]
        for k, v in CANONICAL_ROLES_MAP.items():
            if k in r_low:
                return v
        return role.strip() if role and role.strip() else "Software Development Engineer II"

    async def extract_coding_problem(self, question_text: str, source_url: str = "") -> Optional[Dict[str, Any]]:
        """Extracts problem titles, statements, input/output formats, constraints, and test examples."""
        workflow_state.update_agent_status(self.name, AgentStatus.RUNNING, current_task="Extracting coding problem structure")

        # Check if text describes a coding/algorithmic problem
        is_coding = bool(re.search(r"(\barray\b|\btree\b|\bstring\b|\binput\b|\boutput\b|\bconstraints\b|\bimplement\b|\bgiven\b|\bcomplexity\b)", question_text, re.IGNORECASE))
        if not is_coding and len(question_text) < 40:
            workflow_state.update_agent_status(self.name, AgentStatus.COMPLETED)
            return None

        # Extract title
        title = question_text.split("\n")[0][:120].strip()
        if title.lower().startswith("problem statement:"):
            title = title[18:].strip()

        # Extract constraints if present
        constraints = None
        con_match = re.search(r"constraints?:?\s*([^\n]+(?:\n[^\n]+)?)", question_text, re.IGNORECASE)
        if con_match:
            constraints = con_match.group(1).strip()

        # Extract input/output formats
        input_fmt = None
        in_match = re.search(r"input format:?\s*([^\n]+)", question_text, re.IGNORECASE)
        if in_match:
            input_fmt = in_match.group(1).strip()

        output_fmt = None
        out_match = re.search(r"output format:?\s*([^\n]+)", question_text, re.IGNORECASE)
        if out_match:
            output_fmt = out_match.group(1).strip()

        # Extract examples if present
        examples = []
        ex_matches = re.findall(r"(example\s*\d?:?\s*[^\n]+(?:\n[^\n]+)?)", question_text, re.IGNORECASE)
        for ex in ex_matches:
            examples.append({"example_text": ex.strip()})

        problem_data = {
            "title": title or "Algorithmic Challenge",
            "statement": question_text,
            "input_format": input_fmt,
            "output_format": output_fmt,
            "constraints": constraints,
            "examples": examples if examples else None,
            "languages": "Python, C++, Java",
            "concepts": "Data Structures & Algorithms",
            "source_reference": source_url,
        }

        workflow_state.update_agent_status(self.name, AgentStatus.COMPLETED)
        return problem_data

    async def extract_questions_from_full_article(
        self,
        article_content: str,
        company: str,
        role: str,
        url: str = "",
        platform: str = "Open Web",
    ) -> List[Dict[str, Any]]:
        """
        Processes full trafilatura article bodies through the Nemotron extraction gate.
        Gating rules:
        - Drops opinion pieces, generic tutorials, salary rants, or non-interviews -> returns []
        - Splits substantive debriefs into 3-8 clean, standalone questions with exact rounds and canonical categories
        - Normalizes role and canonicalizes text with <NUM> masking
        """
        workflow_state.update_agent_status(
            self.name, AgentStatus.RUNNING, current_task=f"Gating full article for {company} via Nemotron"
        )

        norm_role = self._normalize_role(role)
        article_text = (article_content or "").strip()
        if len(article_text) < 400:
            workflow_state.update_agent_status(self.name, AgentStatus.COMPLETED)
            return []

        # 1. Attempt LLM Gate if Nemotron / Ollama is available
        if await self.nemotron.is_available():
            schema_desc = (
                "{\n"
                '  "is_interview_experience": boolean,\n'
                '  "reason": string,\n'
                '  "questions": [\n'
                '    {\n'
                '      "question_text": "standalone problem statement without preamble",\n'
                '      "round_number": 1 to 5,\n'
                '      "interview_round": "e.g. Round 2: Core Coding & Algorithms",\n'
                '      "difficulty": "Easy" | "Medium" | "Hard",\n'
                '      "category": "one of: Arrays and Strings, Trees and Graphs, Dynamic Programming, System Design, Operating Systems, DBMS and SQL, Computer Networks, Object-Oriented Programming, Machine Learning, Product Management, HR and Behavioral, Linked Lists",\n'
                '      "skills": ["Skill1", "Skill2"]\n'
                '    }\n'
                '  ]\n'
                "}"
            )

            prompt = (
                f"You are analyzing a candidate's write-up for an interview at {company} for the role '{norm_role}'.\n"
                "Article Text:\n"
                f"{article_text[:10000]}\n\n"
                "Instructions:\n"
                "1. If this is an opinion piece, salary rant, generic listicle, or general article, set is_interview_experience to false and questions to [].\n"
                "2. If this is a real first-hand candidate interview debrief, extract every technical problem, system design prompt, or behavioral question.\n"
                "3. Ensure every question_text is standalone and contains the complete problem requirements.\n"
                "4. Category MUST strictly be one of the canonical categories in the schema.\n"
            )

            try:
                res = await self.nemotron.extract_structured_json(prompt, schema_desc)
                if res and res.get("is_interview_experience") and res.get("questions"):
                    validated_qs = []
                    for q in res.get("questions", []):
                        raw_q = strip_question_wrappers(q.get("question_text", ""))
                        if len(raw_q) < 30:
                            continue
                        cat = q.get("category", "")
                        if cat not in CANONICAL_CATEGORIES:
                            cat = self.nlp.classify_question(raw_q)["category"]

                        validated_qs.append({
                            "company_name": company,
                            "job_role": norm_role,
                            "question_text": raw_q,
                            "question_category": cat,
                            "difficulty": q.get("difficulty", "Medium"),
                            "round_number": int(q.get("round_number", 2)),
                            "interview_round": q.get("interview_round", f"Round {q.get('round_number', 2)}: Technical Assessment"),
                            "skills_tested": q.get("skills", [cat]),
                            "source_platform": platform,
                            "original_url": url,
                            "confidence_score": 0.95,
                        })
                    if validated_qs:
                        workflow_state.update_agent_status(self.name, AgentStatus.COMPLETED)
                        return validated_qs
            except Exception as e:
                logger.warning(f"Nemotron extraction failed, using heuristic fallback gate: {e}")

        # 2. Resilient Deterministic Fallback Gate
        extracted = self.nlp.extract_interview_entities(article_text, source_url=url)
        candidate_qs = extracted.get("questions_with_rounds") or []

        validated_qs = []
        seen_hashes = set()

        for item in candidate_qs:
            if isinstance(item, tuple):
                q_text_raw = item[0]
                r_num = item[1]
                r_name = item[2]
            elif isinstance(item, dict):
                q_text_raw = item.get("question_text", "")
                r_num = int(item.get("round_number", 2))
                r_name = item.get("interview_round", f"Round {r_num}: Technical Assessment")
            else:
                q_text_raw = str(item)
                r_num, r_name = 2, "Round 2: Technical Assessment"

            q_text = strip_question_wrappers(q_text_raw)
            if len(q_text) < 30 or len(q_text) > 800:
                continue

            q_hash = get_dedup_hash(q_text)
            if q_hash in seen_hashes:
                continue
            seen_hashes.add(q_hash)

            cls = self.nlp.classify_question(q_text)
            validated_qs.append({
                "company_name": company,
                "job_role": norm_role,
                "question_text": q_text,
                "question_category": cls["category"],
                "difficulty": cls["difficulty"],
                "round_number": r_num,
                "interview_round": r_name,
                "skills_tested": [cls["category"]],
                "source_platform": platform,
                "original_url": url,
                "confidence_score": 0.90,
            })

        workflow_state.update_agent_status(self.name, AgentStatus.COMPLETED)
        return validated_qs
