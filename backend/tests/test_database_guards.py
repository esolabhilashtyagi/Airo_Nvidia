import os
import subprocess
from pathlib import Path

import pytest

import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
_venv_py = BACKEND_DIR / "venv" / "bin" / "python"
PYTHON = _venv_py if _venv_py.exists() else Path(sys.executable)


def test_pytest_database_resolver_rejects_non_test_name_without_leaking_password():
    from app.core.database_guards import resolve_and_validate_test_database

    with pytest.raises(ValueError) as error:
        resolve_and_validate_test_database(
            "postgresql+asyncpg://dbuser:secret@localhost:5432/aairo_development",
        )

    assert "aairo_development" in str(error.value)
    assert "***" in str(error.value)
    assert "secret" not in str(error.value)


def test_pytest_database_resolver_accepts_explicitly_allowed_database():
    from app.core.database_guards import resolve_and_validate_test_database

    assert resolve_and_validate_test_database(
        "postgresql+asyncpg://dbuser:secret@localhost:5432/custom_ci_db",
        explicit_allowed="custom_ci_db",
    ) == "custom_ci_db"


def test_pytest_session_guard_aborts_non_test_target_before_connecting():
    env = os.environ.copy()
    env.update({
        "DATABASE_URL": "postgresql+asyncpg://dbuser:secret@127.0.0.1:1/aairo_development",
        "DATABASE_URL_SYNC": "postgresql+psycopg2://dbuser:secret@127.0.0.1:1/aairo_development",
        "GEMINI_API_KEY": "",
        "DISABLE_SQLALCHEMY_CEXT": "1",
    })
    env.pop("TEST_DB_ALLOWED", None)

    result = subprocess.run(
        [str(PYTHON), "-m", "pytest", "--collect-only", "-q", "tests/test_database_guards.py"],
        cwd=BACKEND_DIR, env=env, capture_output=True, text=True, timeout=15,
    )

    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "Refusing to run pytest against non-test database" in output
    assert "OperationalError" not in output
    assert "secret" not in output


def test_seed_entrypoint_refuses_without_allowlist_before_connecting():
    env = os.environ.copy()
    env.update({
        "DATABASE_URL": "postgresql+asyncpg://dbuser:secret@127.0.0.1:1/seed_guard_test",
        "DATABASE_URL_SYNC": "postgresql+psycopg2://dbuser:secret@127.0.0.1:1/seed_guard_test",
        "ENVIRONMENT": "development",
        "DISABLE_SQLALCHEMY_CEXT": "1",
    })
    env.pop("SEED_ALLOWED_DB", None)

    result = subprocess.run(
        [str(PYTHON), "-m", "app.core.seed"], cwd=BACKEND_DIR, env=env,
        capture_output=True, text=True, timeout=15,
    )

    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "SEED_ALLOWED_DB is required" in output
    assert "OperationalError" not in output
    assert "secret" not in output


def test_seed_entrypoint_refuses_production_even_with_allowlist():
    from app.core.database_guards import validate_seed_target

    with pytest.raises(RuntimeError, match="refuses to run in production"):
        validate_seed_target(
            "postgresql://dbuser:secret@localhost:5432/aairo_phase4_pytest",
            allowed_database="aairo_phase4_pytest",
            environment="production",
        )


def test_public_content_bootstrap_requires_exact_production_database_allowlist():
    from app.core.database_guards import validate_public_content_bootstrap_target

    url = "postgresql+asyncpg://dbuser:secret@localhost:5432/aairo_prod"
    assert validate_public_content_bootstrap_target(
        url, allowed_database="aairo_prod", environment="production"
    ) == "aairo_prod"
    with pytest.raises(RuntimeError, match="PUBLIC_CONTENT_BOOTSTRAP_ALLOWED_DB"):
        validate_public_content_bootstrap_target(
            url, allowed_database=None, environment="production"
        )
    with pytest.raises(RuntimeError, match="does not match"):
        validate_public_content_bootstrap_target(
            url, allowed_database="another_database", environment="production"
        )
    with pytest.raises(RuntimeError, match="reserved for production"):
        validate_public_content_bootstrap_target(
            url, allowed_database="aairo_prod", environment="development"
        )
