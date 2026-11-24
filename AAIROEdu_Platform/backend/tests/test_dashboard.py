import pytest
from httpx import AsyncClient


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
