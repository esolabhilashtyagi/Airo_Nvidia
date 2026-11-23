"""
Agent 11: Database Management Agent.
Stores and updates extracted interview records, coding problems, and source attribution
in PostgreSQL / SQLite, maintaining relationships and handling database transactions.
"""

from typing import Dict, Any, Optional, Tuple
from core.workflow_state import workflow_state, AgentStatus
from database.repository import get_db_repository
from database.models import InterviewQuestion


class DatabaseManagementAgent:
    def __init__(self):
        self.name = "DatabaseManagementAgent"
        workflow_state.register_agent(self.name, agent_type="STORAGE_ENGINE")
        self.db = get_db_repository()

    async def store_question(
        self,
        company: str,
        role: str,
        question_text: str,
        category: str,
        difficulty: str,
        platform: str,
        url: str,
        experience_level: str = "Mid",
        confidence: float = 0.85,
        coding_data: Optional[Dict[str, Any]] = None,
        round_number: int = 1,
        interview_round: Optional[str] = None,
    ) -> Tuple[InterviewQuestion, bool]:
        workflow_state.update_agent_status(self.name, AgentStatus.RUNNING, current_task="Persisting interview question")
        
        # Ensure company & role records exist
        self.db.get_or_create_company(company)
        self.db.get_or_create_job_role(role)

        question, is_new = self.db.insert_interview_question(
            company_name=company,
            job_role=role,
            question_text=question_text,
            question_category=category,
            difficulty=difficulty,
            source_platform=platform,
            original_url=url,
            experience_level=experience_level,
            confidence_score=confidence,
            coding_problem_data=coding_data,
            round_number=round_number,
            interview_round=interview_round,
        )

        workflow_state.update_agent_status(self.name, AgentStatus.COMPLETED)
        return question, is_new
