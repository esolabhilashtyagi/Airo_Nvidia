"""
Classification Pipeline stage.
Assigns categories, difficulty ratings, and domain classifications to questions.
"""

from typing import Dict, Any
from agents.classification_agent import QuestionClassificationAgent


class ClassificationPipeline:
    def __init__(self):
        self.classifier = QuestionClassificationAgent()

    async def process_question(self, question_text: str) -> Dict[str, str]:
        return await self.classifier.classify_question(question_text)
