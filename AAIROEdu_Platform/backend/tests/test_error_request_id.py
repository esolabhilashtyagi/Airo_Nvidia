import asyncio
import json

import pytest
from sqlalchemy.exc import OperationalError
from starlette.requests import Request

from app.main import http_exception_handler, unhandled_exception_handler


def _request(request_id: str) -> Request:
    request = Request({
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/v1/auth/login",
        "raw_path": b"/api/v1/auth/login",
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("test", 80),
    })
    request.state.request_id = request_id
    return request


def test_http_error_response_preserves_generated_request_id():
    from fastapi import HTTPException

    response = asyncio.run(
        http_exception_handler(_request("req-http-test"), HTTPException(status_code=401, detail="Unauthorized"))
    )
    assert json.loads(response.body)["request_id"] == "req-http-test"


def test_unhandled_error_response_preserves_generated_request_id():
    response = asyncio.run(
        unhandled_exception_handler(_request("req-500-test"), RuntimeError("private test detail"))
    )
    body = json.loads(response.body)
    assert response.status_code == 500
    assert body["request_id"] == "req-500-test"
    assert body["error"]["message"] == "An unexpected error occurred. Please try again later."


def test_database_connection_failure_returns_actionable_503_and_request_id():
    from sqlalchemy.exc import OperationalError

    error = OperationalError("SELECT 1", None, ConnectionRefusedError("[Errno 61] Connection refused"))
    response = asyncio.run(unhandled_exception_handler(_request("req-db-down"), error))
    body = json.loads(response.body)

    assert response.status_code == 503
    assert body["request_id"] == "req-db-down"
    assert body["error"]["code"] == "DATABASE_UNAVAILABLE"
    assert body["error"]["message"] == "The database is unreachable. Make sure PostgreSQL is running."
    assert response.headers["Retry-After"] == "5"
    assert response.headers["X-Request-ID"] == "req-db-down"
    assert "ConnectionRefusedError" not in body["error"]["message"]


def test_missing_database_table_returns_migration_diagnostic_without_exposing_sql():
    from sqlalchemy.exc import ProgrammingError

    class UndefinedTableError(Exception):
        sqlstate = "42P01"

    error = ProgrammingError("SELECT * FROM auth_attempt_limits", {}, UndefinedTableError("missing table"))
    response = asyncio.run(unhandled_exception_handler(_request("req-schema-mismatch"), error))
    body = json.loads(response.body)

    assert response.status_code == 503
    assert body["request_id"] == "req-schema-mismatch"
    assert body["error"]["code"] == "DATABASE_SCHEMA_MISMATCH"
    assert "migration state" in body["error"]["message"]
    assert "auth_attempt_limits" not in body["error"]["message"]


@pytest.mark.parametrize(("sqlstate", "error_code", "message"), [
    ("28P01", "DATABASE_AUTHENTICATION_FAILED", "The database rejected its configured credentials. Check the local database configuration."),
    ("3D000", "DATABASE_NOT_FOUND", "The configured database name does not exist. Verify the local database target."),
])
def test_database_configuration_errors_are_not_misreported_as_network_outages(sqlstate, error_code, message):
    class PostgresConfigurationError(Exception):
        pass

    underlying = PostgresConfigurationError("synthetic private database detail")
    underlying.sqlstate = sqlstate
    error = OperationalError("SELECT 1", {}, underlying)
    response = asyncio.run(unhandled_exception_handler(_request("req-db-config"), error))
    body = json.loads(response.body)

    assert response.status_code == 503
    assert body["error"]["code"] == error_code
    assert body["error"]["message"] == message
    assert "synthetic private database detail" not in response.body.decode()
    assert response.headers["Retry-After"] == "5"


@pytest.mark.parametrize("database_error", [False, True], ids=["application-pii", "sql-parameters"])
def test_unhandled_exception_logs_only_class_and_request_id(caplog, database_error):
    import logging

    email = "zz_test_private_log@example.com"
    password = "ZzTestPrivateLog123!"
    sql = "SELECT hashed_password FROM users WHERE email = :email AND password = :password"
    private_detail = f"private detail: {email} {password}"
    error = (
        OperationalError(sql, {"email": email, "password": password}, RuntimeError(private_detail))
        if database_error else RuntimeError(private_detail)
    )
    request_id = "req-redacted-log"
    with caplog.at_level(logging.ERROR, logger="aairo"):
        try:
            raise error
        except Exception as exc:
            response = asyncio.run(unhandled_exception_handler(_request(request_id), exc))

    assert response.status_code == (503 if database_error else 500)
    assert json.loads(response.body)["request_id"] == request_id
    records = [record for record in caplog.records if record.name == "aairo"]
    assert len(records) == 1
    assert records[0].getMessage() == (
        f"Unhandled system exception (request_id={request_id}, type={type(error).__name__})"
    )
    assert records[0].exc_info is None
    assert records[0].stack_info is None
    for sensitive in (email, password, sql, private_detail):
        assert sensitive not in caplog.text
        assert sensitive not in response.body.decode()
