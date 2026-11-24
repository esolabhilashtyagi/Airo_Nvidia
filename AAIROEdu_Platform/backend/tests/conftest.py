import os
import sys
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.core.config import settings
from app.core.database import async_engine
from app.core.database_guards import resolve_and_validate_test_database


def pytest_sessionstart(session):
    try:
        resolve_and_validate_test_database(
            settings.DATABASE_URL,
            explicit_allowed=os.environ.get("TEST_DB_ALLOWED"),
        )
    except ValueError as exc:
        pytest.exit(str(exc), returncode=pytest.ExitCode.USAGE_ERROR)


@pytest_asyncio.fixture(scope="function", autouse=True)
async def reset_engine():
    yield
    await async_engine.dispose()


@pytest_asyncio.fixture
async def async_client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client


@pytest_asyncio.fixture
async def candidate_token(async_client: AsyncClient):
    # Log in as demo candidate
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "candidate@aairo.ai", "password": "CandidatePass123!"}
    )
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token = login_res.json()["data"]["access_token"]
    return token


@pytest_asyncio.fixture
async def candidate_headers(candidate_token: str):
    return {"Authorization": f"Bearer {candidate_token}"}


@pytest_asyncio.fixture
async def admin_token(async_client: AsyncClient):
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": settings.INITIAL_ADMIN_EMAIL, "password": settings.INITIAL_ADMIN_PASSWORD}
    )
    assert login_res.status_code == 200, f"Admin login failed: {login_res.text}"
    token = login_res.json()["data"]["access_token"]
    return token


@pytest_asyncio.fixture
async def admin_headers(admin_token: str):
    return {"Authorization": f"Bearer {admin_token}"}
