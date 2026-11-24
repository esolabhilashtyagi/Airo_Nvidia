#!/usr/bin/env bash
# Owner-only migration workflow for the local Compose development database.
# Never run this automatically, in CI, or from an agent session.
set -euo pipefail
umask 077

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT/backend"
ENV_FILE="${AAIRO_ENV_FILE:-$ROOT/.env}"
BACKUP_DIR="${AAIRO_BACKUP_DIR:-$ROOT/backups}"
ALEMBIC_BIN="${AAIRO_ALEMBIC_BIN:-$BACKEND_DIR/venv/bin/alembic}"
SEED=0
ok() { printf 'OK: %s\n' "$*"; }
fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }

if [ "$#" -gt 1 ]; then fail "Usage: ./scripts/migrate_dev_db.sh [--seed]"; fi
if [ "${1:-}" = "--seed" ]; then SEED=1
elif [ "$#" -gt 0 ]; then fail "Unknown option: $1"
fi

command -v docker >/dev/null 2>&1 || fail "Docker CLI is not installed"
docker info >/dev/null 2>&1 || fail "Docker daemon is unavailable; open Docker Desktop before continuing"
[ -r "$ENV_FILE" ] || fail "Cannot read repo-root .env; create it from .env.example"

TARGET="$(python3 - "$ENV_FILE" <<'PY'
import re, sys
from urllib.parse import unquote, urlsplit
values = {}
with open(sys.argv[1], encoding="utf-8") as f:
    for raw in f:
        match = re.match(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$", raw)
        if not match:
            continue
        key, value = match.groups()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        else:
            value = re.split(r"\s+#", value, maxsplit=1)[0].strip()
        values[key] = value
parsed = urlsplit(values.get("DATABASE_URL", ""))
if parsed.scheme not in {"postgres", "postgresql", "postgresql+asyncpg", "postgresql+psycopg"}:
    raise SystemExit("DATABASE_URL must be a PostgreSQL URL")
host, port = parsed.hostname or "", parsed.port or 5432
user, password = unquote(parsed.username or ""), unquote(parsed.password or "")
database = unquote(parsed.path.lstrip("/"))
environment = values.get("ENVIRONMENT", "development")
if not host or not user or not database:
    raise SystemExit("DATABASE_URL must include host, username, and database")
print("\t".join((host, str(port), user, database, password, environment)))
PY
)" || fail "Could not safely parse PostgreSQL target from repo-root .env"
IFS=$'\t' read -r DB_HOST DB_PORT DB_USER DB_NAME DB_PASSWORD FILE_ENVIRONMENT <<EOF
$TARGET
EOF
unset TARGET
ENVIRONMENT="${ENVIRONMENT:-$FILE_ENVIRONMENT}"
if [ "$DB_HOST" != "localhost" ] && [ "$DB_HOST" != "127.0.0.1" ]; then
  fail "Refusing owner migration for non-local DATABASE_URL host '$DB_HOST'"
fi
if [ "$DB_PORT" != "5432" ]; then
  fail "Compose PostgreSQL is published on port 5432, but DATABASE_URL selects port $DB_PORT"
fi
printf 'Target: postgresql://%s@%s:%s/%s (password redacted)\n' "$DB_USER" "$DB_HOST" "$DB_PORT" "$DB_NAME"

case "$DB_NAME" in *_pytest) fail "Refusing development migration of test database '$DB_NAME'" ;; esac
if [ "$(printf '%s' "$ENVIRONMENT" | tr '[:upper:]' '[:lower:]')" = "production" ]; then
  fail "Refusing development migration when ENVIRONMENT=production"
fi
cat <<EOF
WARNING: migration a4f2c7d9e108 deactivates ambiguous or unowned assessments; its downgrade does not restore those flags.
EOF
printf 'Type the exact database name to confirm this development database migration (%s): ' "$DB_NAME"
IFS= read -r CONFIRMATION || fail "No confirmation received"
[ "$CONFIRMATION" = "$DB_NAME" ] || fail "Database name confirmation did not match; no backup or migration was run"
ok "Exact database-name confirmation received"

mkdir -p "$BACKUP_DIR"
timestamp="$(date -u '+%Y%m%dT%H%M%SZ')"
BACKUP_FILE="$BACKUP_DIR/${DB_NAME}_$timestamp.dump"
[ ! -e "$BACKUP_FILE" ] || fail "Backup path already exists; refusing to overwrite it: $BACKUP_FILE"
if ! docker compose exec -T postgres pg_dump -U "$DB_USER" -Fc "$DB_NAME" >"$BACKUP_FILE"; then
  rm -f "$BACKUP_FILE"
  fail "Database backup failed; migration was not run"
fi
if [ ! -s "$BACKUP_FILE" ]; then
  rm -f "$BACKUP_FILE"
  fail "Database backup was empty; migration was not run"
fi
ok "Verified non-empty backup: $BACKUP_FILE"
printf 'Backup restore command if needed (stop the app first; this overwrites matching database objects):\n  docker compose exec -T postgres pg_restore -U %s -d %s --clean --if-exists < %s\n' "$DB_USER" "$DB_NAME" "$BACKUP_FILE"

[ -x "$BACKEND_DIR/venv/bin/python" ] || fail "Backend virtual environment is missing"
[ -x "$ALEMBIC_BIN" ] || fail "Alembic executable is missing at $ALEMBIC_BIN"
export DATABASE_URL
DATABASE_URL="$(python3 - "$ENV_FILE" <<'PY'
import re, sys
for raw in open(sys.argv[1], encoding="utf-8"):
    match = re.match(r"^\s*(?:export\s+)?DATABASE_URL\s*=\s*(.*?)\s*$", raw)
    if match:
        value = match.group(1)
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        else:
            value = re.split(r"\s+#", value, maxsplit=1)[0].strip()
        print(value)
        break
else:
    raise SystemExit("DATABASE_URL is missing")
PY
)"
export DATABASE_URL_SYNC
DATABASE_URL_SYNC="$(cd "$BACKEND_DIR" && ./venv/bin/python -c 'import os; from app.core.alembic_target import derive_sync_url; print(derive_sync_url(os.environ["DATABASE_URL"]))')"
export ALEMBIC_ALLOWED_DB="$DB_NAME"
cd "$BACKEND_DIR"

printf 'Current database revision:\n'
"$ALEMBIC_BIN" current
printf 'Source Alembic head(s):\n'
"$ALEMBIC_BIN" heads
printf 'Applying Alembic upgrade head to explicitly confirmed database %s...\n' "$DB_NAME"
"$ALEMBIC_BIN" upgrade head
ok "Alembic upgrade head completed"
printf 'Checking model/schema drift:\n'
"$ALEMBIC_BIN" check
ok "Alembic check completed"

if [ "$SEED" -eq 1 ]; then
  printf 'WARNING: demo seed creates accounts with publicly known passwords. Type exactly "SEED %s" to continue: ' "$DB_NAME"
  IFS= read -r SEED_CONFIRMATION || fail "No seed confirmation received"
  [ "$SEED_CONFIRMATION" = "SEED $DB_NAME" ] || fail "Seed confirmation did not match; no seed was run"
  printf 'Running demo seed only after the second confirmation.\n'
  SEED_ALLOWED_DB="$DB_NAME" ENVIRONMENT="$ENVIRONMENT" "$BACKEND_DIR/venv/bin/python" -m app.core.seed
  ok "Demo seed command completed"
elif [ "${1:-}" != "" ]; then
  fail "Unexpected argument: $1"
fi
