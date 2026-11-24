#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$REPO_ROOT/backend"
TEST_DB_NAME="${AAIRO_TEST_DB_NAME:-aairo_phase4_pytest}"

cd "$BACKEND_DIR"
export DATABASE_URL="${AAIRO_TEST_DATABASE_URL:-postgresql+asyncpg://aairo_user:aairo_secure_password@localhost:5432/${TEST_DB_NAME}}"
if [[ "${AAIRO_TEST_UNSET_ALLOWLIST:-0}" == "1" ]]; then
  unset ALEMBIC_ALLOWED_DB
else
  export ALEMBIC_ALLOWED_DB="$TEST_DB_NAME"
fi

# Derive the sync driver URL from the async URL. Keep the credential-bearing
# rendering in this process environment; only the redacted URL is printed.
export DATABASE_URL_SYNC="$(./venv/bin/python -c 'import os; from app.core.alembic_target import derive_sync_url; print(derive_sync_url(os.environ["DATABASE_URL"]))')"

./venv/bin/python - <<'PY'
import os
from app.core.alembic_target import redact_database_url

print(f"Alembic async target: {redact_database_url(os.environ['DATABASE_URL'])}")
print(f"Alembic sync target:  {redact_database_url(os.environ['DATABASE_URL_SYNC'])}")
PY

if (($# == 0)); then
  set -- upgrade head
fi
exec ./venv/bin/alembic "$@"
