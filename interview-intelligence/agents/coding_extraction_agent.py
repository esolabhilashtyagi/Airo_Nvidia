"""
Agent 6: Coding Problem Extraction Agent.
Extracts problem titles, statements, input/output formats, constraints, and test examples.
Does NOT fabricate or invent missing constraints or examples.
"""

import re
from typing import Dict, Any, Optional
from core.workflow_state import workflow_state, AgentStatus
from core.logging import logger


class CodingProblemExtractionAgent:
    def __init__(self):
        self.name = "CodingProblemExtractionAgent"
        workflow_state.register_agent(self.name, agent_type="DETERMINISTIC_EXTRACTION")

    async def extract_coding_problem(self, question_text: str, source_url: str = "") -> Optional[Dict[str, Any]]:
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
