"""
Verification Pipeline stage.
Evaluates authenticity, identifies first-person narratives vs generic tutorials,
and assigns confidence scoring.
"""

from typing import Dict, Any
from agents.verification_agent import AuthenticityVerificationAgent


class VerificationPipeline:
    def __init__(self):
        self.verifier = AuthenticityVerificationAgent()

    async def process_text(self, text: str) -> Dict[str, Any]:
        return await self.verifier.verify_record(text)
