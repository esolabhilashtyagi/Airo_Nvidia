"""
Agent 10: Data Enrichment Agent.
Standardizes company names, normalizes job titles, extracts technical skills and tech stack tags.
Maintains original source attribution and never fabricates missing information.
"""

import re
from typing import Dict, Any, List
from core.workflow_state import workflow_state, AgentStatus


class DataEnrichmentAgent:
    def __init__(self):
        self.name = "DataEnrichmentAgent"
        workflow_state.register_agent(self.name, agent_type="ENRICHER")
        
        self.company_canonical_map = {
            "google inc": "Google",
            "alphabet": "Google",
            "amazon web services": "Amazon",
            "aws": "Amazon",
            "microsoft corp": "Microsoft",
            "msft": "Microsoft",
            "meta platforms": "Meta",
            "facebook": "Meta",
            "apple inc": "Apple",
            "nvidia corp": "NVIDIA",
            "netflix inc": "Netflix",
            "uber technologies": "Uber",
            "gfg": "GeeksforGeeks",
        }

        self.tech_skill_keywords = [
            "Python", "C++", "Java", "Go", "Rust", "TypeScript", "JavaScript",
            "Kubernetes", "Docker", "PostgreSQL", "Redis", "Kafka", "Elasticsearch",
            "AWS", "GCP", "Azure", "PyTorch", "TensorFlow", "CUDA", "FastAPI",
            "Spring Boot", "React", "GraphQL", "gRPC", "Linux"
        ]

    def enrich_experience(self, exp_data: Dict[str, Any]) -> Dict[str, Any]:
        workflow_state.update_agent_status(self.name, AgentStatus.RUNNING, current_task="Enriching entities & skills")
        enriched = dict(exp_data)
        
        # 1. Standardize company name
        raw_comp = exp_data.get("company_name", "").strip()
        canonical_comp = self.company_canonical_map.get(raw_comp.lower(), raw_comp.title())
        enriched["company_name"] = canonical_comp

        # 2. Normalize job title
        raw_role = exp_data.get("job_role", "").strip()
        normalized_role = raw_role
        if re.search(r"\b(sde\s*1|sde\s*i)\b", raw_role, re.IGNORECASE):
            normalized_role = "Software Development Engineer I"
        elif re.search(r"\b(sde\s*2|sde\s*ii)\b", raw_role, re.IGNORECASE):
            normalized_role = "Software Development Engineer II"
        elif re.search(r"\b(sde\s*3|sde\s*iii|senior sde)\b", raw_role, re.IGNORECASE):
            normalized_role = "Senior Software Development Engineer"
        enriched["job_role"] = normalized_role

        # 3. Extract technical skills
        full_text = exp_data.get("raw_text", "")
        extracted_skills = []
        for skill in self.tech_skill_keywords:
            if re.search(rf"\b{re.escape(skill)}\b", full_text, re.IGNORECASE):
                extracted_skills.append(skill)
        enriched["detected_skills"] = extracted_skills

        workflow_state.update_agent_status(self.name, AgentStatus.COMPLETED)
        return enriched
