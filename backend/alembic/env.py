import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Add backend directory to sys.path so app modules are resolvable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.alembic_target import resolve_alembic_target
from app.core.config import settings
import app.models  # Ensures all models and enums are registered
from app.core.database import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Alembic derives its sync URL from the same DATABASE_URL the app uses. Validate
# the actual target before creating an engine or allowing any migration DDL.
allowed_db = os.environ.get("ALEMBIC_ALLOWED_DB")
if not allowed_db and (os.environ.get("RENDER") or os.environ.get("ENVIRONMENT") == "production"):
    from sqlalchemy.engine import make_url
    try:
        parsed_target_url = make_url(settings.DATABASE_URL)
        if parsed_target_url.database and not parsed_target_url.database.endswith("_pytest"):
            allowed_db = parsed_target_url.database
    except Exception:
        pass

alembic_target = resolve_alembic_target(
    settings.DATABASE_URL,
    allowed_db,
)
config.set_main_option("sqlalchemy.url", alembic_target.sync_url.replace("%", "%%"))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
