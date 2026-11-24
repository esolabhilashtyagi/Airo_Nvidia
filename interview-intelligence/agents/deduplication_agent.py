"""
Agent 9: Deduplication Agent.
Detects exact duplicates via SHA256 content hashing, near-duplicates via token Jaccard similarity,
and records duplicate linkages while preserving source attribution.
Enforces canonical wrapper stripping and numerical value masking (<NUM>) to eliminate synthetic clones.
"""

import hashlib
import re
from typing import Tuple, Optional
from core.workflow_state import workflow_state, AgentStatus
from database.repository import get_db_repository
from database.models import InterviewQuestion, DuplicateRecord
from models.fallback_models import strip_question_wrappers, canonicalize_text, get_dedup_hash


class DeduplicationAgent:
    def __init__(self):
        self.name = "DeduplicationAgent"
        workflow_state.register_agent(self.name, agent_type="DEDUPLICATOR")
        self.db = get_db_repository()

    def check_duplicate(self, company: str, question_text: str) -> Tuple[bool, Optional[str]]:
        """
        Checks whether the question is an exact duplicate or near duplicate.
        Strips wrapper boilerplate and masks numbers (<NUM>) before checking.
        Returns: (is_duplicate, original_question_id)
        """
        workflow_state.update_agent_status(self.name, AgentStatus.RUNNING, current_task="Evaluating duplicate status")

        # 1. Canonical Content Hash (strips wrappers and normalizes numbers)
        canon_text = canonicalize_text(question_text)
        content_hash = get_dedup_hash(question_text)
        comp_clean = company.lower().strip()

        with self.db.get_session() as session:
            # Check exact canonical hash match
            exact_match = session.query(InterviewQuestion).filter(
                InterviewQuestion.content_hash == content_hash
            ).first()
            if exact_match:
                workflow_state.update_agent_status(self.name, AgentStatus.COMPLETED)
                return True, exact_match.id

            # 2. Near-duplicate token Jaccard similarity within same company
            comp_questions = session.query(InterviewQuestion).filter(
                InterviewQuestion.company_name.ilike(comp_clean)
            ).limit(200).all()

            tokens_new = set(re.findall(r"\w+", canon_text))
            if len(tokens_new) >= 4:
                for q in comp_questions:
                    q_canon = canonicalize_text(q.question_text)
                    tokens_existing = set(re.findall(r"\w+", q_canon))
                    if not tokens_existing:
                        continue
                    jaccard = len(tokens_new & tokens_existing) / len(tokens_new | tokens_existing)
                    if jaccard >= 0.82:  # High canonical similarity threshold
                        # Record duplicate linkage
                        dup_entry = DuplicateRecord(
                            original_question_id=q.id,
                            duplicate_question_id="PENDING_DUPLICATE",
                            similarity_score=float(jaccard),
                            duplicate_type="NEAR_DUPLICATE_JACCARD",
                        )
                        session.add(dup_entry)
                        session.commit()
                        workflow_state.update_agent_status(self.name, AgentStatus.COMPLETED)
                        return True, q.id

        workflow_state.update_agent_status(self.name, AgentStatus.COMPLETED)
        return False, None
