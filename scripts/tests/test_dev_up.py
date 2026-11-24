import os
import stat
import subprocess
from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "dev_up.sh"
CONFIG = Config(str(ROOT / "backend" / "alembic.ini"))
CONFIG.set_main_option("script_location", str(ROOT / "backend" / "alembic"))
HEAD = ScriptDirectory.from_config(CONFIG).get_heads()[0]


@pytest.fixture
def fake_environment(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DATABASE_URL='postgresql+asyncpg://aairo_user:super-secret-test-value@localhost:5432/aairo_db'\n",
        encoding="utf-8",
    )
    docker = bin_dir / "docker"
    docker.write_text(
        """#!/bin/sh
if [ "$1" = info ]; then
  [ "$SCENARIO" != daemon_down ] || exit 1
  exit 0
fi
if [ "$1" = ps ]; then
  [ "$SCENARIO" != port_conflict ] || printf 'aairo-db 0.0.0.0:5432->5432/tcp\n'
  exit 0
fi
if [ "$1" = compose ] && [ "$2" = up ]; then exit 0; fi
if [ "$1" = compose ] && [ "$2" = logs ]; then echo 'stub postgres logs'; exit 0; fi
if [ "$1" = compose ] && [ "$2" = exec ]; then
  case "$*" in
    *pg_isready*) [ "$SCENARIO" != unhealthy ] && exit 0 || exit 1 ;;
    *version_num*)
      [ "$SCENARIO" != schema_behind ] && printf '%s\n' "$CODE_HEAD"
      [ "$SCENARIO" != schema_behind ] && exit 0 || exit 1
      ;;
    *select*1*)
      case "$SCENARIO" in
        password_failure) echo 'FATAL: password authentication failed for user' >&2; exit 1 ;;
        database_missing) echo 'FATAL: database "aairo_db" does not exist' >&2; exit 1 ;;
        *) echo 1; exit 0 ;;
      esac
      ;;
  esac
fi
exit 0
""",
        encoding="utf-8",
    )
    docker.chmod(docker.stat().st_mode | stat.S_IXUSR)
    sleep = bin_dir / "sleep"
    sleep.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    sleep.chmod(sleep.stat().st_mode | stat.S_IXUSR)
    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}:{env['PATH']}",
            "AAIRO_ENV_FILE": str(env_file),
            "SCENARIO": "success",
            "CODE_HEAD": HEAD,
        }
    )
    return env


def run_dev_up(env, *args):
    return subprocess.run(
        ["bash", str(SCRIPT), "--db-only", *args],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )


def test_daemon_down_exits_with_docker_desktop_guidance(fake_environment):
    fake_environment["SCENARIO"] = "daemon_down"
    result = run_dev_up(fake_environment)
    assert result.returncode != 0
    assert "Open Docker Desktop, wait until it is running, then rerun" in result.stderr


def test_other_container_port_conflict_prints_stop_command_without_stopping(fake_environment):
    fake_environment["SCENARIO"] = "port_conflict"
    result = run_dev_up(fake_environment)
    assert result.returncode != 0
    assert "aairo-db" in result.stderr
    assert "docker stop aairo-db" in result.stderr
    assert "super-secret-test-value" not in result.stdout + result.stderr


def test_unhealthy_service_times_out_and_shows_compose_logs(fake_environment):
    fake_environment["SCENARIO"] = "unhealthy"
    result = run_dev_up(fake_environment)
    assert result.returncode != 0
    assert "did not become healthy within 60 seconds" in result.stderr
    assert "stub postgres logs" in result.stderr


@pytest.mark.parametrize(
    ("scenario", "message"),
    [
        ("password_failure", "credentials do not match"),
        ("database_missing", "Database aairo_db does not exist"),
    ],
)
def test_credential_failures_are_actionable_and_do_not_leak_password(fake_environment, scenario, message):
    fake_environment["SCENARIO"] = scenario
    result = run_dev_up(fake_environment)
    assert result.returncode != 0
    assert message in result.stderr
    assert "super-secret-test-value" not in result.stdout + result.stderr


def test_schema_behind_stops_before_starting_app_and_points_to_migrator(fake_environment):
    fake_environment["SCENARIO"] = "schema_behind"
    result = run_dev_up(fake_environment)
    assert result.returncode != 0
    assert "Run ./scripts/migrate_dev_db.sh" in result.stderr


def test_schema_equal_passes_db_only_and_redacts_password(fake_environment):
    result = run_dev_up(fake_environment)
    assert result.returncode == 0, result.stderr
    assert "OK: Database Alembic revision matches source head(s)" in result.stdout
    assert "OK: --db-only requested" in result.stdout
    assert "super-secret-test-value" not in result.stdout + result.stderr
