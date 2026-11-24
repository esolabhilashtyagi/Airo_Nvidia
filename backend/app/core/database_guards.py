from sqlalchemy.engine import URL, make_url


def _parse_database_url(database_url: str | URL) -> URL:
    try:
        return make_url(database_url)
    except Exception as exc:
        raise ValueError("Database URL is invalid; refusing to proceed") from exc


def resolve_and_validate_test_database(
    database_url: str | URL,
    explicit_allowed: str | None = None,
) -> str:
    url = _parse_database_url(database_url)
    database_name = url.database
    if not database_name:
        raise ValueError("Test database URL has no database name; refusing to run pytest")
    db_base = database_name.replace("\\", "/").split("/")[-1]
    if (
        database_name.endswith("_pytest")
        or db_base.endswith("_pytest")
        or db_base.endswith("_pytest.db")
        or database_name == explicit_allowed
        or db_base == explicit_allowed
    ):
        return database_name

    redacted_url = url.render_as_string(hide_password=True)
    raise ValueError(
        f"Refusing to run pytest against non-test database {redacted_url}; "
        "database name must end in '_pytest' or exactly match TEST_DB_ALLOWED"
    )


def validate_seed_target(
    database_url: str | URL,
    allowed_database: str | None,
    environment: str,
) -> str:
    if environment.lower() == "production":
        raise RuntimeError("Seed command refuses to run in production")
    if not allowed_database or not allowed_database.strip():
        redacted_url = _parse_database_url(database_url).render_as_string(hide_password=True)
        raise RuntimeError(
            f"SEED_ALLOWED_DB is required for seed commands (resolved target {redacted_url}); refusing to seed"
        )

    url = _parse_database_url(database_url)
    if not url.database:
        raise RuntimeError("Seed database URL has no database name; refusing to seed")
    if url.database != allowed_database:
        redacted_url = url.render_as_string(hide_password=True)
        raise RuntimeError(
            f"Seed target {redacted_url} does not match SEED_ALLOWED_DB {allowed_database!r}; refusing to seed"
        )
    return url.database


def validate_taxonomy_bootstrap_target(
    database_url: str | URL,
    allowed_database: str | None,
    environment: str,
) -> str:
    """Allow only an explicitly allowlisted production taxonomy bootstrap."""
    if environment.lower() != "production":
        raise RuntimeError("Taxonomy bootstrap is reserved for production deployments")
    if not allowed_database or not allowed_database.strip():
        raise RuntimeError("TAXONOMY_BOOTSTRAP_ALLOWED_DB is required; refusing to bootstrap")

    url = _parse_database_url(database_url)
    if not url.database:
        raise RuntimeError("Taxonomy bootstrap database URL has no database name")
    if url.database != allowed_database:
        raise RuntimeError(
            f"Taxonomy bootstrap target {url.database!r} does not match "
            f"TAXONOMY_BOOTSTRAP_ALLOWED_DB {allowed_database!r}; refusing to bootstrap"
        )
    return url.database


def validate_public_content_bootstrap_target(
    database_url: str | URL,
    allowed_database: str | None,
    environment: str,
) -> str:
    """Allow the idempotent published-content bootstrap only for an exact production DB allowlist."""
    if environment.lower() != "production":
        raise RuntimeError("Public content bootstrap is reserved for production deployments")
    if not allowed_database or not allowed_database.strip():
        raise RuntimeError("PUBLIC_CONTENT_BOOTSTRAP_ALLOWED_DB is required; refusing to bootstrap")

    url = _parse_database_url(database_url)
    if not url.database:
        raise RuntimeError("Public content bootstrap database URL has no database name")
    if url.database != allowed_database:
        raise RuntimeError(
            f"Public content bootstrap target {url.database!r} does not match "
            "PUBLIC_CONTENT_BOOTSTRAP_ALLOWED_DB; refusing to bootstrap"
        )
    return url.database
