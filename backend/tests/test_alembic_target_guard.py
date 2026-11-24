import os
import subprocess
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
MIGRATION_SCRIPT = BACKEND_DIR.parent / "scripts" / "migrate_test_db.sh"


def _alembic_env(database_url: str) -> dict[str, str]:
    env = os.environ.copy()
    env.update({
        "DATABASE_URL": database_url,
        "DATABASE_URL_SYNC": "postgresql://ignored:ignored@127.0.0.1:1/wrong_sync_target",
        "GEMINI_API_KEY": "",
    })
    return env


def test_alembic_env_refuses_target_database_not_allowlisted():
    env = _alembic_env("postgresql+asyncpg://user:secret@127.0.0.1:1/not_the_allowed_db")
    env["AAIRO_TEST_DATABASE_URL"] = env.pop("DATABASE_URL")
    env["AAIRO_TEST_DB_NAME"] = "aairo_phase4_pytest"

    result = subprocess.run(
        [str(MIGRATION_SCRIPT), "current"], cwd=BACKEND_DIR.parent, env=env,
        capture_output=True, text=True, timeout=15,
    )

    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "not_the_allowed_db" in output
    assert "aairo_phase4_pytest" in output
    assert "refusing to connect" in output.lower()
    assert "OperationalError" not in output
    assert "secret" not in output


def test_alembic_env_refuses_when_allowlist_is_unset():
    env = _alembic_env("postgresql+asyncpg://user:secret@127.0.0.1:1/aairo_phase4_pytest")
    env["AAIRO_TEST_DATABASE_URL"] = env.pop("DATABASE_URL")
    env["AAIRO_TEST_DB_NAME"] = "aairo_phase4_pytest"
    env["AAIRO_TEST_UNSET_ALLOWLIST"] = "1"

    result = subprocess.run(
        [str(MIGRATION_SCRIPT), "current"], cwd=BACKEND_DIR.parent, env=env,
        capture_output=True, text=True, timeout=15,
    )

    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "ALEMBIC_ALLOWED_DB is required" in output
    assert "OperationalError" not in output
    assert "secret" not in output


def test_target_resolver_uses_database_url_and_redacts_password():
    from app.core.alembic_target import resolve_alembic_target

    target = resolve_alembic_target(
        "postgresql+asyncpg://user:secret@localhost:5432/aairo_phase4_pytest",
        "aairo_phase4_pytest",
    )

    assert target.database_name == "aairo_phase4_pytest"
    assert target.sync_url.startswith("postgresql://")
    assert "secret" not in target.redacted_sync_url
    assert "secret" not in target.redacted_url
    assert "***" in target.redacted_url
