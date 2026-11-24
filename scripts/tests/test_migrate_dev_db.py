import os
import stat
import subprocess
from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "migrate_dev_db.sh"
CONFIG = Config(str(ROOT / "backend" / "alembic.ini"))
CONFIG.set_main_option("script_location", str(ROOT / "backend" / "alembic"))
HEAD = ScriptDirectory.from_config(CONFIG).get_heads()[0]


@pytest.fixture
def migration_environment(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DATABASE_URL='postgresql+asyncpg://aairo_user:do-not-print-this@localhost:5432/aairo_db'\n"
        "ENVIRONMENT=development\n",
        encoding="utf-8",
    )
    docker = bin_dir / "docker"
    docker.write_text(
        """#!/bin/sh
if [ "$1" = info ]; then exit 0; fi
if [ "$1" = compose ] && [ "$2" = exec ]; then
  case "$*" in
    *pg_dump*)
      [ "$SCENARIO" != backup_failure ] || exit 1
      [ "$SCENARIO" != backup_empty ] || exit 0
      printf 'verified synthetic custom-format dump'
      exit 0
      ;;
  esac
fi
exit 0
""",
        encoding="utf-8",
    )
    docker.chmod(docker.stat().st_mode | stat.S_IXUSR)
    alembic_log = tmp_path / "alembic.log"
    alembic = bin_dir / "alembic"
    alembic.write_text(
        """#!/bin/sh
printf '%s|%s\n' "$ALEMBIC_ALLOWED_DB" "$*" >> "$ALEMBIC_LOG"
case "$1" in
  current) echo 'Current revision(s) for aairo_db: 4f2a' ;;
  heads) echo "$CODE_HEAD (head)" ;;
  upgrade) echo 'upgrade simulated' ;;
  check) echo 'No new upgrade operations detected.' ;;
esac
""",
        encoding="utf-8",
    )
    alembic.chmod(alembic.stat().st_mode | stat.S_IXUSR)
    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}:{env['PATH']}",
            "AAIRO_ENV_FILE": str(env_file),
            "AAIRO_BACKUP_DIR": str(tmp_path / "backups"),
            "AAIRO_ALEMBIC_BIN": str(alembic),
            "ALEMBIC_LOG": str(alembic_log),
            "CODE_HEAD": HEAD,
            "SCENARIO": "success",
        }
    )
    return env, env_file, tmp_path, alembic_log


def run_migration(env, input_text="", *args):
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        cwd=ROOT,
        env=env,
        input=input_text,
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )


def test_wrong_database_confirmation_refuses_before_backup_or_alembic(migration_environment):
    env, _env_file, tmp_path, alembic_log = migration_environment
    result = run_migration(env, "not-the-database\n")
    assert result.returncode != 0
    assert "confirmation did not match" in result.stderr
    assert not (tmp_path / "backups").exists()
    assert not alembic_log.exists()
    assert "do-not-print-this" not in result.stdout + result.stderr


@pytest.mark.parametrize(
    ("database_url", "environment", "expected"),
    [
        ("postgresql+asyncpg://u:p@localhost:5432/aairo_phase4_pytest", "development", "test database"),
        ("postgresql+asyncpg://u:p@localhost:5432/aairo_db", "production", "ENVIRONMENT=production"),
    ],
)
def test_refuses_test_or_production_database_before_confirmation(
    migration_environment, database_url, environment, expected
):
    env, env_file, tmp_path, alembic_log = migration_environment
    env_file.write_text(f"DATABASE_URL='{database_url}'\nENVIRONMENT={environment}\n", encoding="utf-8")
    result = run_migration(env)
    assert result.returncode != 0
    assert expected in result.stderr
    assert not (tmp_path / "backups").exists()
    assert not alembic_log.exists()


@pytest.mark.parametrize("scenario", ["backup_failure", "backup_empty"])
def test_missing_or_failed_backup_aborts_before_migration(migration_environment, scenario):
    env, _env_file, tmp_path, alembic_log = migration_environment
    env["SCENARIO"] = scenario
    result = run_migration(env, "aairo_db\n")
    assert result.returncode != 0
    assert "backup" in result.stderr.lower()
    assert not alembic_log.exists()
    backups = tmp_path / "backups"
    assert not backups.exists() or not list(backups.glob("*.dump"))


def test_success_backs_up_then_runs_guarded_current_upgrade_and_check(migration_environment):
    env, _env_file, tmp_path, alembic_log = migration_environment
    result = run_migration(env, "aairo_db\n")
    assert result.returncode == 0, result.stderr
    assert "password redacted" in result.stdout
    assert "Alembic upgrade head completed" in result.stdout
    assert "deactivates ambiguous or unowned assessments" in result.stdout
    assert "pg_restore" in result.stdout
    assert "do-not-print-this" not in result.stdout + result.stderr
    assert len(list((tmp_path / "backups").glob("*.dump"))) == 1
    commands = alembic_log.read_text(encoding="utf-8").splitlines()
    assert [line.split("|", 1)[1] for line in commands] == ["current", "heads", "upgrade head", "check"]
    assert all(line.startswith("aairo_db|") for line in commands)


def test_seed_requires_its_own_typed_confirmation(migration_environment):
    env, _env_file, tmp_path, alembic_log = migration_environment
    result = run_migration(env, "aairo_db\nwrong-seed-confirmation\n", "--seed")
    assert result.returncode != 0
    assert "Seed confirmation did not match" in result.stderr
    assert "publicly known passwords" in result.stdout
    assert len(list((tmp_path / "backups").glob("*.dump"))) == 1
    assert "do-not-print-this" not in result.stdout + result.stderr
