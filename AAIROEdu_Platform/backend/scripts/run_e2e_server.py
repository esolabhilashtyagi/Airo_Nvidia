"""Create/reuse an isolated E2E database, migrate it, and serve the API.

Never drops or resets a database. The default database name is deliberately
different from the development database. Upload files live in a temporary dir.
"""
from __future__ import annotations

import os
import re
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

import psycopg2
from sqlalchemy.engine import make_url

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
MIGRATION_SCRIPT = REPO_ROOT / "scripts" / "migrate_test_db.sh"
os.chdir(BACKEND_DIR)
sys.path.insert(0, str(BACKEND_DIR))
from app.core.config import settings  # noqa: E402


def main() -> None:
    database_name = os.getenv("AAIRO_E2E_DATABASE", "aairo_phase3_e2e")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", database_name):
        raise SystemExit("AAIRO_E2E_DATABASE must be a simple PostgreSQL identifier.")
    if database_name == settings.POSTGRES_DB:
        raise SystemExit("Refusing to use the configured development database for E2E tests.")

    connection = psycopg2.connect(
        host=settings.POSTGRES_SERVER,
        port=settings.POSTGRES_PORT,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        dbname="postgres",
    )
    try:
        # CREATE DATABASE is not allowed inside a PostgreSQL transaction block.
        connection.autocommit = True
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (database_name,))
            if cursor.fetchone() is None:
                cursor.execute(f'CREATE DATABASE "{database_name}"')
    finally:
        connection.close()

    environment = os.environ.copy()
    environment["DATABASE_URL"] = make_url(settings.DATABASE_URL).set(database=database_name).render_as_string(hide_password=False)
    environment["DATABASE_URL_SYNC"] = make_url(settings.DATABASE_URL_SYNC).set(database=database_name).render_as_string(hide_password=False)
    environment["AAIRO_TEST_DB_NAME"] = database_name
    environment["AAIRO_TEST_DATABASE_URL"] = environment["DATABASE_URL"]
    environment["SEED_ALLOWED_DB"] = database_name
    environment["POSTGRES_DB"] = database_name
    # Seed demo administrator/candidate accounts and clearly test-only content
    # in this isolated E2E database. These records are never written to the
    # configured development or production database.
    environment["INITIAL_ADMIN_EMAIL"] = "phase4-admin-e2e@example.com"
    environment["INITIAL_ADMIN_PASSWORD"] = "Phase4E2EAdminPass123!"
    port = int(os.getenv("AAIRO_E2E_API_PORT", "8001"))

    with tempfile.TemporaryDirectory(prefix="aairo-e2e-uploads-") as upload_directory:
        environment["UPLOAD_DIR"] = upload_directory
        subprocess.run([str(MIGRATION_SCRIPT), "upgrade", "head"], cwd=REPO_ROOT, env=environment, check=True)
        subprocess.run([sys.executable, "-m", "app.core.seed"], cwd=BACKEND_DIR, env=environment, check=True)
        server = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
            cwd=BACKEND_DIR,
            env=environment,
        )

        def stop_server(_signum, _frame):
            if server.poll() is None:
                server.terminate()

        signal.signal(signal.SIGTERM, stop_server)
        signal.signal(signal.SIGINT, stop_server)
        try:
            exit_code = server.wait()
        finally:
            if server.poll() is None:
                server.terminate()
                server.wait(timeout=10)
        raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
