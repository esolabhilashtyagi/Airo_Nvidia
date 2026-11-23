"""
End-to-end multi-agent pipeline integration test.
"""

import pytest
from agents.orchestrator import MasterOrchestratorAgent
from database.repository import get_db_repository


@pytest.mark.asyncio
async def test_end_to_end_pipeline_execution():
    orchestrator = MasterOrchestratorAgent()
    summary = await orchestrator.run_pipeline(source_name="all", limit=2, use_mock=True)

    assert summary["status"] == "COMPLETED"
    assert summary["collected"] > 0
    # Verified deduplication or new indexing
    assert summary["indexed"] > 0 or summary["duplicates"] > 0

    # Verify records in database
    db = get_db_repository()
    analytics = db.get_analytics_summary()
    assert analytics["total_questions"] > 0
    assert analytics["total_companies"] > 0
