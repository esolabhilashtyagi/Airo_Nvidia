"""
Extraction Pipeline stage.
Integrates ExperienceExtractionAgent and CodingProblemExtractionAgent.
"""

from typing import Dict, Any, List
from agents.experience_extraction_agent import ExperienceExtractionAgent
from agents.coding_extraction_agent import CodingProblemExtractionAgent


class ExtractionPipeline:
    def __init__(self):
        self.exp_extractor = ExperienceExtractionAgent()
        self.code_extractor = CodingProblemExtractionAgent()

    async def process(self, document: Dict[str, Any]) -> Dict[str, Any]:
        exp_data = await self.exp_extractor.extract_experience(
            document["raw_text"], document.get("original_url", "")
        )
        
        parsed_questions = []
        for q_text in exp_data.get("questions", []):
            coding_data = await self.code_extractor.extract_coding_problem(
                q_text, document.get("original_url", "")
            )
            parsed_questions.append({
                "question_text": q_text,
                "coding_problem": coding_data,
            })

        exp_data["parsed_questions"] = parsed_questions
        return exp_data
