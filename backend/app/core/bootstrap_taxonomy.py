"""Idempotently install baseline industry taxonomy for a deployment database.

This deliberately does not create demo users, questions, assessments, or modules.
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.alembic_target import resolve_alembic_target
from app.core.database_guards import validate_taxonomy_bootstrap_target
from app.core.seed import COMPANIES_SEED, INITIAL_INDUSTRIES
from app.models.candidate import Company
from app.models.taxonomy import Industry, IndustryCategory, JobRole


def ensure_baseline_taxonomy(db: Session) -> tuple[int, int, int, int]:
    """Insert missing industries, roles, categories, and company suggestions."""
    industries_added = 0
    categories_added = 0
    roles_added = 0
    companies_added = 0

    for item in INITIAL_INDUSTRIES:
        industry = db.query(Industry).filter(Industry.slug == item["slug"]).first()
        if industry is None:
            industry = Industry(
                name=item["name"],
                slug=item["slug"],
                description=item["description"],
                icon=item["icon"],
                is_active=True,
            )
            db.add(industry)
            db.flush()
            industries_added += 1

        for category_name in item.get("categories", []):
            category = db.query(IndustryCategory).filter(
                IndustryCategory.industry_id == industry.id,
                IndustryCategory.name == category_name,
            ).first()
            if category is None:
                db.add(IndustryCategory(
                    industry_id=industry.id,
                    name=category_name,
                    is_active=True,
                ))
                categories_added += 1

        for title, description, experience_level in item.get("roles", []):
            role = db.query(JobRole).filter(
                JobRole.industry_id == industry.id,
                JobRole.title == title,
            ).first()
            if role is None:
                db.add(JobRole(
                    industry_id=industry.id,
                    title=title,
                    description=description,
                    experience_level=experience_level,
                    is_active=True,
                ))
                roles_added += 1

    for item in COMPANIES_SEED:
        company = db.query(Company).filter(Company.name == item["name"]).first()
        if company is None:
            db.add(Company(
                name=item["name"],
                industry=item.get("industry"),
                website=item.get("website"),
                is_active=True,
            ))
            companies_added += 1

    db.commit()
    return industries_added, categories_added, roles_added, companies_added


def main() -> None:
    target_database = validate_taxonomy_bootstrap_target(
        settings.DATABASE_URL,
        allowed_database=os.environ.get("TAXONOMY_BOOTSTRAP_ALLOWED_DB"),
        environment=settings.ENVIRONMENT,
    )
    # Derive the synchronous driver from the same managed URL Alembic uses.
    # DATABASE_URL_SYNC may be absent on hosts such as Render and otherwise
    # silently falls back to a localhost development default.
    target = resolve_alembic_target(
        settings.DATABASE_URL,
        allowed_database=target_database,
    )
    engine = create_engine(target.sync_url, hide_parameters=True, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = session_factory()
    try:
        added = ensure_baseline_taxonomy(db)
        print(
            "Baseline taxonomy bootstrap completed for "
            f"allowlisted database {target.database_name}: "
            f"{added[0]} industries, {added[1]} categories, "
            f"{added[2]} roles, {added[3]} companies added."
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
        engine.dispose()


if __name__ == "__main__":
    main()
