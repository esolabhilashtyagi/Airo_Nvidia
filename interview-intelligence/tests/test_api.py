"""
API tests for FastAPI endpoints using async test transport.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from api.main import app


@pytest.mark.asyncio
async def test_api_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # /health
        r_health = await client.get("/health")
        assert r_health.status_code == 200
        assert r_health.json()["status"] == "HEALTHY"
        assert r_health.json()["free_stack_verified"] is True

        # /analytics
        r_analytics = await client.get("/analytics")
        assert r_analytics.status_code == 200

        # /companies
        r_comp = await client.get("/companies")
        assert r_comp.status_code == 200

        # /questions
        r_q = await client.get("/questions?limit=10")
        assert r_q.status_code == 200

        # /agents/status
        r_agents = await client.get("/agents/status")
        assert r_agents.status_code == 200

        # /collect/start
        r_start = await client.post("/collect/start?source_name=reddit&limit=1&use_mock=true")
        assert r_start.status_code == 200
        assert r_start.json()["status"] == "ACCEPTED"

        # /industries
        r_ind = await client.get("/industries")
        assert r_ind.status_code == 200
        assert "Fintech" in r_ind.json()["industries"]

        # /intelligence/interview-blueprint (POST) Case A
        payload_a = {
            "company_name": "Google",
            "role": "SDE 2",
            "years_of_experience": 4.0,
            "skills": ["Python", "Algorithms"],
        }
        r_bp = await client.post("/intelligence/interview-blueprint", json=payload_a)
        assert r_bp.status_code == 200
        data_bp = r_bp.json()
        assert data_bp["total_rounds"] == 5
        assert len(data_bp["rounds"]) == 5

        # /intelligence/interview-blueprint (GET) Case B
        r_bp_get = await client.get("/intelligence/interview-blueprint?industry=Fintech&role=Backend+Engineer&yoe=3.5&skills=Kafka,PostgreSQL")
        assert r_bp_get.status_code == 200
        data_get = r_bp_get.json()
        assert data_get["target_type"] == "STARTUP_INDUSTRY"
        assert len(data_get["rounds"]) == 4
