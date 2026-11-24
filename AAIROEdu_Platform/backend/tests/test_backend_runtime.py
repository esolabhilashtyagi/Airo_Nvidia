import pytest
from httpx import AsyncClient, ASGITransport

from app.core.config import settings
from app.integrations.ai import provider_factory
from app.main import _api_documentation_urls, app


def test_production_api_documentation_is_disabled_but_remains_available_in_development():
    assert _api_documentation_urls("production") == {
        "docs_url": None,
        "redoc_url": None,
        "openapi_url": None,
    }
    assert _api_documentation_urls("development") == {
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "openapi_url": "/api/v1/openapi.json",
    }


def test_testing_routes_register_with_valid_response_models():
    paths = app.openapi()["paths"]

    assert "/api/v1/testing/configure" in paths
    assert "/api/v1/testing/quiz" in paths


@pytest.mark.asyncio
async def test_root_and_ai_status_routes_boot_without_database_or_provider_call(monkeypatch):
    monkeypatch.setattr(settings, "AI_PROVIDER", "nvidia")
    monkeypatch.setattr(settings, "NVIDIA_API_KEY", "")
    monkeypatch.setattr(settings, "NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
    monkeypatch.setattr(provider_factory, "_cached_provider", None)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        root = await client.get("/")
        ai_status = await client.get("/api/v1/system/ai-status")

    assert root.status_code == 200
    assert root.json()["status"] == "online"
    assert root.headers["x-content-type-options"] == "nosniff"
    assert root.headers["x-frame-options"] == "DENY"
    assert root.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert ai_status.status_code == 200
    assert ai_status.json()["data"] == {
        "provider": "NVIDIA Nemotron",
        "model": "nvidia/nemotron-3.5-lightning-30b-a3b",
        "configured": False,
    }


@pytest.mark.asyncio
async def test_production_responses_add_hsts(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://test") as client:
        response = await client.get("/")
    assert response.headers["strict-transport-security"] == "max-age=31536000; includeSubDomains"


@pytest.mark.parametrize("debug", [False, True])
def test_database_engine_construction_never_echoes_sql_and_hides_parameters(debug, monkeypatch):
    import runpy
    from pathlib import Path
    from unittest.mock import patch

    monkeypatch.setattr(settings, "DEBUG", debug)
    database_module = Path(__file__).resolve().parents[1] / "app" / "core" / "database.py"
    with patch("sqlalchemy.create_engine") as sync_factory, patch("sqlalchemy.ext.asyncio.create_async_engine") as async_factory:
        runpy.run_path(str(database_module))

    for factory, expected_url in ((sync_factory, settings.DATABASE_URL_SYNC), (async_factory, settings.DATABASE_URL)):
        factory.assert_called_once()
        assert factory.call_args.args == (expected_url,)
        assert factory.call_args.kwargs["echo"] is False
        assert factory.call_args.kwargs["hide_parameters"] is True


def test_runtime_database_engines_hide_parameters():
    from app.core.database import async_engine, sync_engine

    for engine in (async_engine.sync_engine, sync_engine):
        assert engine.echo is False
        assert engine.hide_parameters is True
