from dataclasses import dataclass

from sqlalchemy.engine import URL, make_url


@dataclass(frozen=True)
class AlembicTarget:
    database_name: str
    sync_url: str
    redacted_url: str
    redacted_sync_url: str


def derive_sync_url(database_url: str) -> str:
    try:
        return make_url(database_url).set(drivername="postgresql").render_as_string(hide_password=False)
    except Exception as exc:
        raise RuntimeError("DATABASE_URL is invalid; refusing to connect") from exc


def redact_database_url(database_url: str) -> str:
    try:
        return make_url(database_url).render_as_string(hide_password=True)
    except Exception:
        return "<invalid database URL>"


def resolve_alembic_target(database_url: str, allowed_database: str | None) -> AlembicTarget:
    if not allowed_database or not allowed_database.strip():
        raise RuntimeError("ALEMBIC_ALLOWED_DB is required; refusing to connect")

    try:
        async_url: URL = make_url(database_url)
    except Exception as exc:
        raise RuntimeError("DATABASE_URL is invalid; refusing to connect") from exc

    database_name = async_url.database
    if not database_name:
        raise RuntimeError("DATABASE_URL must include a database name; refusing to connect")
    if database_name != allowed_database:
        raise RuntimeError(
            f"Resolved Alembic target database {database_name!r} does not match "
            f"ALEMBIC_ALLOWED_DB {allowed_database!r}; refusing to connect"
        )

    sync_url_object = async_url.set(drivername="postgresql")
    sync_url = derive_sync_url(database_url)
    return AlembicTarget(
        database_name=database_name,
        sync_url=sync_url,
        redacted_url=async_url.render_as_string(hide_password=True),
        redacted_sync_url=sync_url_object.render_as_string(hide_password=True),
    )
