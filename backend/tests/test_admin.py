import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_admin_user_activation_is_authorized_and_persisted(
    async_client: AsyncClient, candidate_headers: dict, admin_headers: dict,
):
    email = f"admin-control-{uuid.uuid4()}@example.com"
    password = "SecureAdminControl123!"
    registered = await async_client.post("/api/v1/auth/register", json={
        "email": email, "password": password, "full_name": "Admin Control Test",
    })
    assert registered.status_code == 201, registered.text
    user_id = registered.json()["data"]["id"]
    login = await async_client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    subject_headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}

    denied = await async_client.patch(f"/api/v1/admin/users/{user_id}/active", headers=candidate_headers,
        json={"is_active": False})
    assert denied.status_code == 403

    deactivated = await async_client.patch(f"/api/v1/admin/users/{user_id}/active", headers=admin_headers,
        json={"is_active": False})
    assert deactivated.status_code == 200, deactivated.text
    assert deactivated.json()["data"]["is_active"] is False
    assert (await async_client.get("/api/v1/candidates/profile", headers=subject_headers)).status_code == 403
    assert (await async_client.post("/api/v1/auth/login", json={"email": email, "password": password})).status_code == 403

    reactivated = await async_client.patch(f"/api/v1/admin/users/{user_id}/active", headers=admin_headers,
        json={"is_active": True})
    assert reactivated.status_code == 200, reactivated.text
    assert reactivated.json()["data"]["is_active"] is True
    assert (await async_client.get("/api/v1/candidates/profile", headers=subject_headers)).status_code == 200


@pytest.mark.asyncio
async def test_admin_cannot_deactivate_self(async_client: AsyncClient, admin_headers: dict):
    admin_user = (await async_client.get("/api/v1/auth/me", headers=admin_headers)).json()["data"]
    result = await async_client.patch(f"/api/v1/admin/users/{admin_user['id']}/active", headers=admin_headers,
        json={"is_active": False})
    assert result.status_code == 409
