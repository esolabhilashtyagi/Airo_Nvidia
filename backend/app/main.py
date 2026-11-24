import logging
from pathlib import Path
import time
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from alembic.config import Config
from alembic.script import ScriptDirectory

from app.core.database import async_engine

from app.api.v1 import api_v1_router
from app.core.config import settings
from app.core.database_errors import database_error_response_code

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("aairo")


def _api_documentation_urls(environment: str) -> dict[str, str | None]:
    """Keep interactive API schemas out of production deployments."""
    if environment.strip().lower() == "production":
        return {"docs_url": None, "redoc_url": None, "openapi_url": None}
    return {
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "openapi_url": f"{settings.API_V1_PREFIX}/openapi.json",
    }


def _database_error_message(error_code: str) -> str:
    return {
        "DATABASE_SCHEMA_MISMATCH": "The application database is missing a required table or column. Verify its migration state before retrying.",
        "DATABASE_UNAVAILABLE": "The database is unreachable. Make sure PostgreSQL is running.",
        "DATABASE_AUTHENTICATION_FAILED": "The database rejected its configured credentials. Check the local database configuration.",
        "DATABASE_NOT_FOUND": "The configured database name does not exist. Verify the local database target.",
    }.get(error_code, "An unexpected error occurred. Please try again later.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting Candidate Dashboard AAIRO backend...")
    logger.info(f"Environment: {settings.ENVIRONMENT} | Debug: {settings.DEBUG}")
    if "sqlite" in settings.DATABASE_URL:
        try:
            import app.models
            from app.models.base import Base
            from app.core.database import sync_engine
            Base.metadata.create_all(bind=sync_engine)
            logger.info("✅ SQLite tables verified/created.")
        except Exception as e:
            logger.warning(f"Auto-table creation notice: {e}")
    yield
    logger.info("🛑 Shutting down Candidate Dashboard AAIRO backend...")


app = FastAPI(
    title=settings.APP_NAME,
    description="Industry-Independent AI-Powered Career Preparation & Assessment Platform API",
    version="1.0.0",
    **_api_documentation_urls(settings.ENVIRONMENT),
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing and Request-ID middleware
@app.middleware("http")
async def add_process_time_and_request_id(request: Request, call_next):
    req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = req_id
    start_time = time.time()
    
    try:
        response = await call_next(request)
    except HTTPException as exc:
        response = await http_exception_handler(request, exc)
    except Exception as exc:
        # BaseHTTPMiddleware can wrap endpoint exceptions in ExceptionGroup.
        # Handle here as well as in the registered handler so wrapped driver
        # failures become a response instead of escaping the ASGI stack.
        if isinstance(exc, HTTPException):
            response = await http_exception_handler(request, exc)
        else:
            response = await unhandled_exception_handler(request, exc)
    
    process_time = (time.time() - start_time) * 1000
    response.headers["X-Process-Time-Ms"] = f"{process_time:.2f}"
    response.headers["X-Request-ID"] = req_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if settings.ENVIRONMENT == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# Global Exception Handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = getattr(request.state, "request_id", request.headers.get("X-Request-ID", "unknown"))
    return JSONResponse(
        status_code=exc.status_code,
        headers=exc.headers,
        content={
            "success": False,
            "error": {
                "code": "HTTP_ERROR",
                "message": exc.detail
            },
            "request_id": request_id
        }
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        return await http_exception_handler(request, exc)
    request_id = getattr(request.state, "request_id", request.headers.get("X-Request-ID", "unknown"))
    logger.error("Unhandled system exception (request_id=%s, type=%s)", request_id, type(exc).__name__)
    db_error_code = database_error_response_code(exc)
    if db_error_code == "DATABASE_SCHEMA_MISMATCH":
        logger.error("Database schema mismatch (request_id=%s)", request_id)
    service_unavailable = db_error_code is not None
    response_headers = {"X-Request-ID": request_id}
    if service_unavailable:
        response_headers["Retry-After"] = "5"
    return JSONResponse(
        status_code=(status.HTTP_503_SERVICE_UNAVAILABLE if service_unavailable else status.HTTP_500_INTERNAL_SERVER_ERROR),
        headers=response_headers,
        content={
            "success": False,
            "error": {
                "code": db_error_code or "INTERNAL_SERVER_ERROR",
                "message": _database_error_message(db_error_code) if db_error_code else _database_error_message("INTERNAL_SERVER_ERROR"),
            },
            "request_id": request_id
        }
    )


# Health check endpoints
@app.get("/", tags=["Health"])
async def root():
    return {
        "status": "online",
        "service": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs"
    }


def _database_health_error(request: Request, error_code: str) -> JSONResponse:
    request_id = getattr(request.state, "request_id", request.headers.get("X-Request-ID", "unknown"))
    schema_mismatch = error_code == "DATABASE_SCHEMA_MISMATCH"
    message = _database_error_message(error_code)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        headers={"Retry-After": "5", "X-Request-ID": request_id},
        content={
            "status": "unready" if schema_mismatch else "unhealthy",
            "timestamp": time.time(),
            "database": "connected" if schema_mismatch else "disconnected",
            **({"schema": "out_of_date"} if schema_mismatch else {}),
            "error": {"code": error_code, "message": message},
            "request_id": request_id,
        },
    )


@app.get("/", tags=["Root"])
async def root():
    return {
        "name": settings.APP_NAME,
        "status": "online",
        "api_v1": settings.API_V1_PREFIX,
        "health": "/health",
    }


@app.get("/health", tags=["Health"])
async def health_check(request: Request):
    try:
        async with async_engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception as exc:
        error_code = database_error_response_code(exc)
        if error_code:
            return _database_health_error(request, error_code)
        raise
    return {"status": "healthy", "timestamp": time.time(), "database": "connected"}


@app.get("/health/ready", tags=["Health"])
async def readiness_check(request: Request):
    """Verify database reachability and that the schema is at current Alembic head."""
    try:
        async with async_engine.connect() as connection:
            result = await connection.execute(text("SELECT version_num FROM alembic_version"))
            current_revisions = set(result.scalars().all())
    except Exception as exc:
        error_code = database_error_response_code(exc)
        if error_code:
            return _database_health_error(request, error_code)
        raise

    config_path = Path(__file__).resolve().parent.parent / "alembic.ini"
    migration_config = Config(str(config_path))
    migration_config.set_main_option("script_location", str(config_path.parent / "alembic"))
    script = ScriptDirectory.from_config(migration_config)
    heads = set(script.get_heads())
    if current_revisions != heads:
        request_id = getattr(request.state, "request_id", request.headers.get("X-Request-ID", "unknown"))
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            headers={"Retry-After": "5", "X-Request-ID": request_id},
            content={
                "status": "unready", "database": "connected", "schema": "out_of_date",
                "error": {
                    "code": "DATABASE_SCHEMA_MISMATCH",
                    "message": "The application database schema is not at the current migration revision.",
                },
                "request_id": request_id,
            },
        )
    return {"status": "ready", "database": "connected", "schema": "current"}


# Mount API V1
app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)
