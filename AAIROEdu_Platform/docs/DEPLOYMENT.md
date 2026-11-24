# Deployment configuration

## Render

The `render.yaml` blueprint defines a FastAPI web service, a static Vite frontend, and the managed PostgreSQL database. The backend startup command applies Alembic migrations before starting Uvicorn.

The Alembic safety guard intentionally requires `ALEMBIC_ALLOWED_DB` and compares it with the database name parsed from `DATABASE_URL` before opening a connection. In the Render blueprint, `ALEMBIC_ALLOWED_DB` is set to `aairo_db`, matching the managed database's `databaseName`. Keep those names aligned if the managed database is renamed. Do not remove this allowlist or derive it automatically from `DATABASE_URL`.

After changing `render.yaml`, sync/apply the updated Blueprint configuration in Render and redeploy the backend. If the service is managed outside the Blueprint, set `ALEMBIC_ALLOWED_DB` in the backend service's environment to the exact database name, then redeploy. A deployment log stating `ALEMBIC_ALLOWED_DB is required` means the running service has not received this environment variable; check that the updated Blueprint was synced and that the variable is visible in the backend service settings. Never paste database URLs or credentials into logs or support messages.

For local Docker Compose, the backend's allowlist is derived from the same `POSTGRES_DB` setting used to construct its database URLs. The standalone backend image remains fail-closed: deployments that run its Dockerfile entrypoint must explicitly provide `ALEMBIC_ALLOWED_DB` matching the target database name.
