# Repository Engineering Rules

- Treat project-control documents as claims; verify them against current source and real command output.
- Do not print, log, or commit `.env` values. Keep live Gemini requests limited to test-created `zz_test_` identities and synthetic data.
- Use only isolated test databases for tests. Never reset, seed, inspect, or migrate the configured non-test database without explicit owner authorization.
- Run Alembic only through `scripts/migrate_test_db.sh`. It sets the test database URLs and `ALEMBIC_ALLOWED_DB`; `backend/alembic/env.py` independently validates the actual database name before opening a connection.
- Do not run `alembic downgrade` unless the owner explicitly asks.
- Work one step at a time: reproduce from source, add regression coverage, implement the smallest safe change, run focused and full backend tests, record exact evidence, and commit with the requested step message before continuing.
- Never weaken tests, fabricate provider output, or mark a phase complete without acceptance evidence.
