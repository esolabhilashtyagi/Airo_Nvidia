import errno
import json
import socket

import pytest
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.database import async_engine, get_async_db
from app.main import app, unhandled_exception_handler
from starlette.requests import Request


def _connection_failures():
    refused = ConnectionRefusedError(errno.ECONNREFUSED, "connection refused")
    wrapped = OperationalError("SELECT 1", {}, refused)
    dns = socket.gaierror(socket.EAI_AGAIN, "temporary name resolution failure")
    return [
        pytest.param(refused, id="refused"),
        pytest.param(wrapped, id="wrapped-operational-error"),
        pytest.param(dns, id="dns-error"),
    ]


def _assert_unavailable(response, request_id):
    body = response.json()
    assert response.status_code == 503
    assert body["error"]["code"] == "DATABASE_UNAVAILABLE"
    assert body["request_id"] == request_id
    assert response.headers["Retry-After"] == "5"
    assert response.headers["X-Request-ID"] == request_id
    assert body["error"]["message"] == "The database is unreachable. Make sure PostgreSQL is running."


@pytest.mark.parametrize("db_error", _connection_failures())
@pytest.mark.asyncio
async def test_login_returns_database_unavailable_for_connection_errors(async_client, db_error):
    request_id = "login-db-unavailable-test"

    async def failing_session():
        class Session:
            async def scalar(self, *_args, **_kwargs):
                raise db_error

            async def close(self):
                return None

        yield Session()

    app.dependency_overrides[get_async_db] = failing_session
    try:
        response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "person@example.com", "password": "test-password"},
            headers={"X-Request-ID": request_id},
        )
    finally:
        app.dependency_overrides.pop(get_async_db, None)

    _assert_unavailable(response, request_id)


@pytest.mark.parametrize("db_error", _connection_failures())
@pytest.mark.asyncio
async def test_health_returns_database_unavailable_for_connection_errors(async_client, monkeypatch, db_error):
    request_id = "health-db-unavailable-test"

    def fail_connect(_engine, *_args, **_kwargs):
        raise db_error

    monkeypatch.setattr(AsyncEngine, "connect", fail_connect)
    response = await async_client.get("/health", headers={"X-Request-ID": request_id})

    body = response.json()
    assert response.status_code == 503
    assert body["status"] == "unhealthy"
    assert body["database"] == "disconnected"
    assert body["error"]["code"] == "DATABASE_UNAVAILABLE"
    assert body["request_id"] == request_id
    assert response.headers["Retry-After"] == "5"
    assert response.headers["X-Request-ID"] == request_id


@pytest.mark.asyncio
async def test_undefined_table_returns_migration_diagnostic_without_sql_details():
    class UndefinedTableError(Exception):
        sqlstate = "42P01"

    request = Request({
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
        "method": "POST", "scheme": "http", "path": "/api/v1/auth/login",
        "raw_path": b"/api/v1/auth/login", "query_string": b"", "headers": [],
        "client": ("127.0.0.1", 12345), "server": ("test", 80),
    })
    request.state.request_id = "schema-mismatch-test"
    error = ProgrammingError("SELECT * FROM auth_attempt_limits", {}, UndefinedTableError("missing"))

    response = await unhandled_exception_handler(request, error)
    body = json.loads(response.body)

    assert response.status_code == 503
    assert body["error"]["code"] == "DATABASE_SCHEMA_MISMATCH"
    assert body["request_id"] == "schema-mismatch-test"
    assert "auth_attempt_limits" not in body["error"]["message"]
    assert "migration state" in body["error"]["message"]


@pytest.mark.asyncio
async def test_readiness_reports_schema_revision_mismatch(async_client, monkeypatch):
    class Result:
        def scalars(self):
            return self

        def all(self):
            return ["old_revision"]

    class Connection:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def execute(self, *_args, **_kwargs):
            return Result()

    monkeypatch.setattr(AsyncEngine, "connect", lambda _engine: Connection())
    response = await async_client.get("/health/ready", headers={"X-Request-ID": "readiness-schema-test"})
    body = response.json()

    assert response.status_code == 503
    assert body["status"] == "unready"
    assert body["error"]["code"] == "DATABASE_SCHEMA_MISMATCH"
    assert body["request_id"] == "readiness-schema-test"
    assert response.headers["Retry-After"] == "5"


@pytest.mark.asyncio
async def test_readiness_reports_connection_failure_safely(async_client, monkeypatch):
    error = socket.gaierror(socket.EAI_AGAIN, "private-hostname.example")

    def fail_connect(_engine, *_args, **_kwargs):
        raise error

    monkeypatch.setattr(AsyncEngine, "connect", fail_connect)
    response = await async_client.get("/health/ready", headers={"X-Request-ID": "readiness-db-down-test"})
    body = response.json()

    assert response.status_code == 503
    assert body["error"]["code"] == "DATABASE_UNAVAILABLE"
    assert body["error"]["message"] == "The database is unreachable. Make sure PostgreSQL is running."
    assert body["request_id"] == "readiness-db-down-test"
    assert response.headers["Retry-After"] == "5"
    assert "private-hostname" not in response.text


@pytest.mark.asyncio
async def test_readiness_maps_missing_migration_table_to_schema_mismatch(async_client, monkeypatch):
    class UndefinedTableError(Exception):
        sqlstate = "42P01"

    error = ProgrammingError(
        "SELECT version_num FROM alembic_version",
        {},
        UndefinedTableError("alembic_version is missing"),
    )

    def fail_connect(_engine, *_args, **_kwargs):
        raise error

    monkeypatch.setattr(AsyncEngine, "connect", fail_connect)
    response = await async_client.get("/health/ready", headers={"X-Request-ID": "readiness-no-version-test"})
    body = response.json()

    assert response.status_code == 503
    assert body["status"] == "unready"
    assert body["database"] == "connected"
    assert body["schema"] == "out_of_date"
    assert body["error"]["code"] == "DATABASE_SCHEMA_MISMATCH"
    assert body["request_id"] == "readiness-no-version-test"
    assert response.headers["Retry-After"] == "5"
    assert "alembic_version" not in response.text
