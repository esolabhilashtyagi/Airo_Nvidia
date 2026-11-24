import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock

from app.services.learning_resources import LearningResourceService


@pytest.mark.asyncio
async def test_modules_and_lessons(async_client: AsyncClient, candidate_headers: dict):
    # 1. List modules
    mod_res = await async_client.get("/api/v1/modules", headers=candidate_headers)
    assert mod_res.status_code == 200
    modules = mod_res.json()["data"]
    assert len(modules) > 0
    mod = modules[0]

    # 2. Get module detail
    detail_res = await async_client.get(f"/api/v1/modules/{mod['id']}", headers=candidate_headers)
    assert detail_res.status_code == 200
    detail = detail_res.json()["data"]
    assert len(detail["lessons"]) > 0
    lesson = detail["lessons"][0]

    # 3. Complete lesson
    comp_res = await async_client.post(
        f"/api/v1/modules/{mod['id']}/lessons/{lesson['id']}/complete",
        headers=candidate_headers
    )
    assert comp_res.status_code == 200
    updated_mod = comp_res.json()["data"]
    assert updated_mod["completion_percentage"] > 0
    assert lesson["id"] in updated_mod["completed_lesson_ids"]
    if len(detail["lessons"]) > 1:
        assert updated_mod["completion_percentage"] < 100


@pytest.mark.asyncio
async def test_learning_module_resources_use_module_topic_and_require_access(async_client, candidate_headers, monkeypatch):
    modules = (await async_client.get("/api/v1/modules", headers=candidate_headers)).json()["data"]
    module = modules[0]
    search = AsyncMock(return_value={"articles": [], "videos": [], "article_status": "available", "video_status": "unavailable_api_key_required"})
    monkeypatch.setattr(LearningResourceService, "search", search)
    response = await async_client.get(f"/api/v1/modules/{module['id']}/resources?recent_years=2", headers=candidate_headers)
    assert response.status_code == 200
    assert search.await_args.args[0] == module["title"]
    assert search.await_args.kwargs["recent_years"] == 2
    no_auth = await async_client.get(f"/api/v1/modules/{module['id']}/resources")
    assert no_auth.status_code == 401
