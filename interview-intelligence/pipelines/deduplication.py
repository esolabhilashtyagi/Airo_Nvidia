"""
Deduplication Pipeline stage.
Evaluates exact content hashing and near-duplicate similarity before persistence.
"""

from typing import Tuple, Optional
from agents.deduplication_agent import DeduplicationAgent


class DeduplicationPipeline:
    def __init__(self):
        self.dedup = DeduplicationAgent()

    def check(self, company: str, question_text: str) -> Tuple[bool, Optional[str]]:
        return self.dedup.check_duplicate(company, question_text)
