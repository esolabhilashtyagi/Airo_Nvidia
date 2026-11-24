"""
Agent 12: Semantic Search Agent.
Generates local dense embeddings (all-MiniLM-L6-v2) and performs semantic similarity search
using pgvector cosine distance or high-performance local vector similarity ranking.
"""

from typing import List, Tuple, Dict, Any
from core.workflow_state import workflow_state, AgentStatus
from database.repository import get_db_repository
from models.model_manager import get_model_manager
from database.models import InterviewQuestion


class SemanticSearchAgent:
    def __init__(self):
        self.name = "SemanticSearchAgent"
        workflow_state.register_agent(self.name, agent_type="VECTOR_SEARCH")
        self.db = get_db_repository()
        self.model_manager = get_model_manager()

    async def index_question(self, question_id: str, question_text: str):
        workflow_state.update_agent_status(self.name, AgentStatus.RUNNING, current_task=f"Indexing vector {question_id}")
        vector = self.model_manager.generate_embedding(question_text)
        self.db.save_embedding(question_id, vector)
        workflow_state.update_agent_status(self.name, AgentStatus.COMPLETED)

    async def search_similar(
        self, query_text: str, limit: int = 10, min_similarity: float = 0.60
    ) -> List[Dict[str, Any]]:
        workflow_state.update_agent_status(self.name, AgentStatus.RUNNING, current_task=f"Searching: {query_text[:30]}")
        query_vector = self.model_manager.generate_embedding(query_text)
        results = self.db.search_similar_questions(query_vector, limit=limit, min_similarity=min_similarity)
        
        formatted = []
        for q, sim in results:
            formatted.append({
                "id": q.id,
                "company_name": q.company_name,
                "job_role": q.job_role,
                "question_text": q.question_text,
                "category": q.question_category,
                "difficulty": q.difficulty,
                "similarity_score": round(sim, 3),
                "url": q.original_url,
            })

        workflow_state.update_agent_status(self.name, AgentStatus.COMPLETED)
        return formatted
