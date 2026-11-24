# Deployment configuration

## Render

The `render.yaml` blueprint defines a FastAPI web service, a static Vite frontend, and the managed PostgreSQL database. Backend startup applies Alembic migrations, bootstraps allowlisted baseline content, then starts Uvicorn.

The backend startup also runs `python -m app.core.bootstrap_public_content`. This idempotently inserts missing baseline industries, categories, roles, company suggestions, published learning modules/lessons, and approved baseline questions from the repository catalog. It skips demo users and candidate profiles, preserves existing records, and is restricted to `ENVIRONMENT=production` plus an exact `PUBLIC_CONTENT_BOOTSTRAP_ALLOWED_DB` database-name allowlist. Keep that value aligned with the Render database name. This makes the deployed learning modules and question bank usable on a fresh database, matching the local baseline content; candidates still see modules relevant to their selected industry. Local development can continue using the full, separately guarded seed command.

The Blueprint selects Gemini by default so all AI-powered features (resume analysis, coach and generated learning/practice content) use one configured provider. Create an API key in Google AI Studio, then add it to Render under the `aairo-backend` service's **Environment** as `GEMINI_API_KEY`; the Blueprint marks it `sync: false` so the secret stays in Render. Save and redeploy the backend after adding it. A missing or invalid key will leave the non-AI application available, but AI-powered requests will fail. `GEMINI_MODEL` defaults to `gemini-3.8-flash`.

To use NVIDIA instead, explicitly set `AI_PROVIDER=nvidia` and configure a valid NVIDIA inference API credential in `NVIDIA_API_KEY`. An OpenCode Console key is for OpenCode and will not authenticate against either Gemini or NVIDIA inference APIs. Provider selection is explicit; the app does not silently switch providers after an API failure.

The Alembic safety guard intentionally requires `ALEMBIC_ALLOWED_DB` and compares it with the database name parsed from `DATABASE_URL` before opening a connection. In the Render blueprint, `ALEMBIC_ALLOWED_DB` is set to `aairo_db`, matching the managed database's `databaseName`. Keep those names aligned if the managed database is renamed. Do not remove this allowlist or derive it automatically from `DATABASE_URL`.

After changing `render.yaml`, sync/apply the updated Blueprint configuration in Render and redeploy the backend. If the service is managed outside the Blueprint, set `ALEMBIC_ALLOWED_DB` in the backend service's environment to the exact database name, then redeploy. A deployment log stating `ALEMBIC_ALLOWED_DB is required` means the running service has not received this environment variable; check that the updated Blueprint was synced and that the variable is visible in the backend service settings. Never paste database URLs or credentials into logs or support messages.

For local Docker Compose, the backend's allowlist is derived from the same `POSTGRES_DB` setting used to construct its database URLs. The standalone backend image remains fail-closed: deployments that run its Dockerfile entrypoint must explicitly provide `ALEMBIC_ALLOWED_DB` matching the target database name.
