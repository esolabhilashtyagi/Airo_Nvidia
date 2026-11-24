#!/usr/bin/env bash
# Owner-run local development bootstrap. This script is deliberately never run by CI/agents.
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${AAIRO_ENV_FILE:-$ROOT/.env}"
COMPOSE_SERVICE="postgres"
COMPOSE_CONTAINER="${AAIRO_POSTGRES_CONTAINER:-aairo-postgres}"
BACKEND_LOG="${TMPDIR:-/tmp}/aairo-backend.log"
FRONTEND_LOG="${TMPDIR:-/tmp}/aairo-frontend.log"
BACKEND_PIDFILE="${TMPDIR:-/tmp}/aairo-backend.pid"
FRONTEND_PIDFILE="${TMPDIR:-/tmp}/aairo-frontend.pid"
DB_ONLY=0
NO_FRONTEND=0
RESTART_POLICY=0

ok() { printf 'OK: %s\n' "$*"; }
fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }

while [ "$#" -gt 0 ]; do
  case "$1" in
    --db-only) DB_ONLY=1 ;;
    --no-frontend) NO_FRONTEND=1 ;;
    --restart-policy) RESTART_POLICY=1 ;;
    *) fail "Unknown option: $1" ;;
  esac
  shift
done

if ! command -v docker >/dev/null 2>&1; then
  printf 'FAIL: Docker CLI is not installed. Open Docker Desktop, wait until it is running, then rerun.\n' >&2
  exit 1
fi
if ! docker info >/dev/null 2>&1; then
  printf 'FAIL: Docker daemon is unavailable. Open Docker Desktop, wait until it is running, then rerun.\n' >&2
  exit 1
fi
ok "Docker CLI and daemon are available"

if [ ! -r "$ENV_FILE" ]; then
  fail "Cannot read repo-root .env (expected $ROOT/.env); create it from .env.example"
fi

# Parse only the target fields. Never source .env as shell code and never print its password.
TARGET="$(python3 - "$ENV_FILE" <<'PY'
import os, re, sys
from urllib.parse import unquote, urlsplit

values = {}
with open(sys.argv[1], encoding="utf-8") as env_file:
    for raw in env_file:
        match = re.match(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$", raw)
        if not match:
            continue
        key, value = match.groups()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        else:
            value = re.split(r"\s+#", value, maxsplit=1)[0].strip()
        values[key] = value
url = values.get("DATABASE_URL", "")
parsed = urlsplit(url)
if parsed.scheme not in {"postgres", "postgresql", "postgresql+asyncpg", "postgresql+psycopg"}:
    raise SystemExit("DATABASE_URL must be a PostgreSQL URL")
host = parsed.hostname or ""
port = parsed.port or 5432
user = unquote(parsed.username or "")
password = unquote(parsed.password or "")
database = unquote(parsed.path.lstrip("/"))
if not host or not user or not database:
    raise SystemExit("DATABASE_URL must include host, username, and database")
print("\t".join((host, str(port), user, database, password)))
PY
)" || fail "Could not safely parse the PostgreSQL target from repo-root .env"
IFS=$'\t' read -r DB_HOST DB_PORT DB_USER DB_NAME DB_PASSWORD <<EOF
$TARGET
EOF
unset TARGET
if [ "$DB_HOST" != "localhost" ] && [ "$DB_HOST" != "127.0.0.1" ]; then
  fail "Refusing local Docker bootstrap for non-local DATABASE_URL host '$DB_HOST'"
fi
if [ "$DB_PORT" != "5432" ]; then
  fail "This Compose service publishes PostgreSQL on host port 5432, but DATABASE_URL selects port $DB_PORT"
fi
printf 'OK: .env target parsed (postgresql://%s@%s:%s/%s; password redacted)\n' "$DB_USER" "$DB_HOST" "$DB_PORT" "$DB_NAME"

CONFLICTS="$(docker ps --filter "publish=$DB_PORT" --format '{{.Names}} {{.Ports}}' 2>/dev/null || true)"
while IFS= read -r line; do
  [ -n "$line" ] || continue
  name="${line%% *}"
  if [ "$name" != "$COMPOSE_CONTAINER" ]; then
    printf 'FAIL: Container %s is already publishing host port %s. If you confirm it is safe to stop, run: docker stop %s\n' "$name" "$DB_PORT" "$name" >&2
    exit 1
  fi
done <<EOF
$CONFLICTS
EOF
ok "No other running container publishes host port $DB_PORT"

if ! docker compose up -d "$COMPOSE_SERVICE"; then
  fail "Could not start Compose PostgreSQL service"
fi
ok "Compose PostgreSQL start requested"

healthy=0
for attempt in $(seq 1 30); do
  if docker compose exec -T "$COMPOSE_SERVICE" pg_isready -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1; then
    healthy=1
    break
  fi
  sleep 2
done
if [ "$healthy" -ne 1 ]; then
  printf 'FAIL: PostgreSQL did not become healthy within 60 seconds. Recent logs:\n' >&2
  docker compose logs "$COMPOSE_SERVICE" --tail 30 >&2 || true
  exit 1
fi
ok "PostgreSQL accepts connections"

# Pass the URL password through stdin, not argv or printed output. Force TCP so
# PostgreSQL validates the same password-based credentials used by the app.
psql_app() {
  printf '%s\n' "$DB_PASSWORD" | docker compose exec -T \
    -e "PGUSER=$DB_USER" -e "PGDATABASE=$DB_NAME" "$COMPOSE_SERVICE" \
    sh -c 'IFS= read -r PGPASSWORD || exit 2; export PGPASSWORD; exec psql -h 127.0.0.1 -U "$PGUSER" -d "$PGDATABASE" -tAqc "$1"' sh "$1"
}

if ! credential_result="$(psql_app 'select 1' 2>&1)"; then
  if printf '%s' "$credential_result" | grep -Eqi 'database .* does not exist'; then
    printf 'FAIL: Database %s does not exist. Create it only after confirming the target, with:\n  docker compose exec -T postgres createdb -U %s %s\n' "$DB_NAME" "$DB_USER" "$DB_NAME" >&2
  elif printf '%s' "$credential_result" | grep -Eqi 'password authentication failed'; then
    printf 'FAIL: .env credentials do not match the credentials initialized in the PostgreSQL container. No password or data was changed.\n' >&2
  else
    printf 'FAIL: PostgreSQL credential check failed: %s\n' "$credential_result" >&2
  fi
  exit 1
fi
if [ "$credential_result" != "1" ]; then
  fail "PostgreSQL credential check returned an unexpected result"
fi
ok "Application database credentials verified over TCP"

HEADS="$("$ROOT/backend/venv/bin/python" - "$ROOT/backend/alembic.ini" <<'PY'
import sys
from pathlib import Path
from alembic.config import Config
from alembic.script import ScriptDirectory
config = Config(sys.argv[1])
config.set_main_option("script_location", str(Path(sys.argv[1]).resolve().parent / "alembic"))
script = ScriptDirectory.from_config(config)
print("\n".join(sorted(script.get_heads())))
PY
)" || fail "Could not read Alembic heads from source (backend/venv must have project dependencies)"
CURRENT="$(psql_app 'select version_num from alembic_version' 2>/dev/null)" || CURRENT=""
if [ -z "$CURRENT" ]; then
  printf 'FAIL: The database has no readable Alembic version. Run ./scripts/migrate_dev_db.sh after reviewing its backup and confirmation prompts.\n' >&2
  exit 1
fi
expected="$(printf '%s\n' "$HEADS" | LC_ALL=C sort)"
actual="$(printf '%s\n' "$CURRENT" | sed '/^[[:space:]]*$/d' | LC_ALL=C sort)"
if [ "$actual" != "$expected" ]; then
  printf 'FAIL: Database schema is behind or differs from source Alembic heads. Current: %s; code heads: %s. Run ./scripts/migrate_dev_db.sh\n' \
    "$(printf '%s' "$actual" | tr '\n' ',')" "$(printf '%s' "$expected" | tr '\n' ',')" >&2
  exit 1
fi
ok "Database Alembic revision matches source head(s)"

if [ "$RESTART_POLICY" -eq 1 ]; then
  container_id="$(docker compose ps -q "$COMPOSE_SERVICE")"
  [ -n "$container_id" ] || fail "Compose did not return the postgres container ID"
  docker update --restart unless-stopped "$container_id" >/dev/null || fail "Could not set the postgres restart policy"
  ok "PostgreSQL container restart policy set to unless-stopped"
else
  printf 'OK: Restart policy left unchanged (use --restart-policy to run docker update --restart unless-stopped %s)\n' "$COMPOSE_CONTAINER"
fi

if [ "$DB_ONLY" -eq 1 ]; then
  ok "--db-only requested; stopping after database checks"
  exit 0
fi

if ! command -v curl >/dev/null 2>&1; then
  fail "curl is required to verify backend readiness"
fi
if ! curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1; then
  backend_python="$ROOT/backend/venv/bin/python"
  [ -x "$backend_python" ] || fail "Backend virtual environment is missing; install backend requirements first"
  (cd "$ROOT/backend" && nohup "$backend_python" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload >"$BACKEND_LOG" 2>&1 & echo $! >"$BACKEND_PIDFILE")
fi
backend_ready=0
for attempt in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1; then backend_ready=1; break; fi
  sleep 2
done
if [ "$backend_ready" -ne 1 ]; then
  printf 'FAIL: Backend did not answer /health within 60 seconds. Recent log:\n' >&2
  tail -n 40 "$BACKEND_LOG" >&2 2>/dev/null || true
  exit 1
fi
ok "Backend /health returned HTTP 200"
if ! curl -fsS http://127.0.0.1:8000/health/ready >/dev/null 2>&1; then
  printf 'FAIL: Backend /health/ready did not return HTTP 200; inspect the migration status above and backend log %s\n' "$BACKEND_LOG" >&2
  exit 1
fi
ok "Backend /health/ready returned HTTP 200"

if [ "$NO_FRONTEND" -eq 0 ]; then
  if ! curl -fsS http://127.0.0.1:5173/ >/dev/null 2>&1; then
    command -v npm >/dev/null 2>&1 || fail "npm is required to start the frontend"
    (cd "$ROOT/frontend" && nohup npm run dev -- --host 0.0.0.0 --port 5173 >"$FRONTEND_LOG" 2>&1 & echo $! >"$FRONTEND_PIDFILE")
  fi
  frontend_ready=0
  for attempt in $(seq 1 30); do
    if curl -fsS http://127.0.0.1:5173/ >/dev/null 2>&1; then frontend_ready=1; break; fi
    sleep 2
  done
  if [ "$frontend_ready" -ne 1 ]; then
    printf 'FAIL: Frontend did not answer within 60 seconds. Recent log:\n' >&2
    tail -n 40 "$FRONTEND_LOG" >&2 2>/dev/null || true
    exit 1
  fi
  ok "Frontend returned HTTP 200"
fi
printf 'Development platform ready: frontend http://localhost:5173, backend http://localhost:8000/docs\n'
