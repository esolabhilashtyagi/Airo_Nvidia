import pytest
from datetime import datetime, timezone
from httpx import AsyncClient

from app.schemas.dashboard import ScoreHistoryItem
from app.services.dashboard_service import DashboardService


@pytest.mark.asyncio
async def test_dashboard_overview_and_analytics(async_client: AsyncClient, candidate_headers: dict):
    # 1. Overview
    overview_res = await async_client.get("/api/v1/dashboard/overview", headers=candidate_headers)
    assert overview_res.status_code == 200
    overview = overview_res.json()["data"]
    assert "interview_readiness_score" in overview
    assert "metrics" in overview
    assert len(overview["metrics"]) == 4

    # 2. Analytics
    analytics_res = await async_client.get("/api/v1/dashboard/analytics", headers=candidate_headers)
    assert analytics_res.status_code == 200
    analytics = analytics_res.json()["data"]
    assert "weekly_activity" in analytics
    assert "score_history" in analytics
    assert "topic_performance" in analytics


def test_readiness_estimate_uses_only_available_evidence_and_reports_coverage():
    score, factors = DashboardService._readiness_estimate(
        profile_score=80,
        resume_score=None,
        assessment_score=60,
        interview_score=None,
    )

    assert score == 66.7  # (15 * 80 + 30 * 60) / 45
    assert factors["coverage_percent"] == 45
    assert factors["components"]["resume_alignment"]["included"] is False
    assert factors["components"]["assessment_proficiency"]["score_percent"] == 60.0


def test_readiness_estimate_clamps_scores_to_the_documented_scale():
    score, factors = DashboardService._readiness_estimate(
        profile_score=120,
        resume_score=-10,
        assessment_score=None,
        interview_score=None,
    )

    assert score == 37.5  # (15 * 100 + 25 * 0) / 40
    assert factors["components"]["profile_baseline"]["score_percent"] == 100.0
    assert factors["components"]["resume_alignment"]["score_percent"] == 0.0


def test_score_history_preserves_exact_timezone_aware_completion_timestamp():
    completed_at = datetime(2026, 11, 25, 4, 7, 9, tzinfo=timezone.utc)
    event = ScoreHistoryItem(date="Nov 25 04:07", timestamp=completed_at, score=82, type="assessment")

    assert event.timestamp == completed_at
    assert event.model_dump(mode="json")["timestamp"] == "2026-11-25T04:07:09Z"
