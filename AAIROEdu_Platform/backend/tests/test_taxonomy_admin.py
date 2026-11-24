import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_taxonomy_deactivation_and_reactivation_are_admin_only(
    async_client: AsyncClient, candidate_headers: dict, admin_headers: dict,
):
    profile = (await async_client.get("/api/v1/candidates/profile", headers=candidate_headers)).json()["data"]
    created = await async_client.post("/api/v1/question-taxonomy/manage", headers=admin_headers, json={
        "kind": "category", "name": f"Lifecycle {uuid.uuid4()}", "industry_id": profile["industry_id"],
    })
    assert created.status_code == 201, created.text
    category_id = created.json()["data"]["id"]

    deactivated = await async_client.delete(
        f"/api/v1/question-taxonomy/manage/category/{category_id}", headers=admin_headers,
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["data"]["is_active"] is False

    denied = await async_client.patch(
        f"/api/v1/question-taxonomy/manage/category/{category_id}/active?active=true",
        headers=candidate_headers,
    )
    assert denied.status_code == 403

    reactivated = await async_client.patch(
        f"/api/v1/question-taxonomy/manage/category/{category_id}/active?active=true",
        headers=admin_headers,
    )
    assert reactivated.status_code == 200
    assert reactivated.json()["data"]["is_active"] is True
