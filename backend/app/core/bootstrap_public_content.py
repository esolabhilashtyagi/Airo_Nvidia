"""Idempotently publish the repository's baseline learning and question content.

This command is for the exact production database allowlisted by
PUBLIC_CONTENT_BOOTSTRAP_ALLOWED_DB. It deliberately skips every demo user and
candidate profile created by the local seed command.
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.alembic_target import resolve_alembic_target
from app.core.config import settings
from app.core.database_guards import validate_public_content_bootstrap_target
from app.core.bootstrap_taxonomy import ensure_baseline_taxonomy
from app.core.seed import seed_database


def main() -> None:
    allowed_database = os.environ.get("PUBLIC_CONTENT_BOOTSTRAP_ALLOWED_DB")
    target_database = validate_public_content_bootstrap_target(
        settings.DATABASE_URL,
        allowed_database=allowed_database,
        environment=settings.ENVIRONMENT,
    )
    target = resolve_alembic_target(settings.DATABASE_URL, allowed_database=target_database)
    engine = create_engine(target.sync_url, hide_parameters=True, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = session_factory()
    try:
        ensure_baseline_taxonomy(db)
        seed_database(db, include_demo_accounts=False)
        print(
            "Published baseline learning modules and question-bank content "
            f"for allowlisted database {target.database_name}; demo users and profiles were not seeded."
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
        engine.dispose()


if __name__ == "__main__":
    main()
