import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_notifications_are_authenticated_and_empty_state_is_real(async_client: AsyncClient, candidate_headers: dict):
    anonymous = await async_client.get("/api/v1/system/notifications")
    assert anonymous.status_code == 401
    response = await async_client.get("/api/v1/system/notifications", headers=candidate_headers)
    assert response.status_code == 200
    assert isinstance(response.json()["data"], list)

    missing = await async_client.patch(
        "/api/v1/system/notifications/00000000-0000-0000-0000-000000000000/read",
        headers=candidate_headers,
    )
    assert missing.status_code == 404
