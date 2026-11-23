"""
FastAPI Main Application Entrypoint.
Initializes routes, middleware, Prometheus metrics exporter, and startup lifecycle.
"""

import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
from contextlib import asynccontextmanager

from core.config import settings
from core.logging import logger
from database.repository import get_db_repository
from .routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("==================================================================")
    logger.info("Starting Interview Intelligence & Ethical Data Collection Platform")
    logger.info("100% Free & Open-Source Stack (NVIDIA Nemotron / Local AI Inference)")
    logger.info("==================================================================")
    db = get_db_repository()
    logger.info(f"Database dialect active: {db.dialect_name}")
    yield
    # Shutdown
    logger.info("Interview Intelligence Platform shutting down gracefully.")


app = FastAPI(
    title="Interview Intelligence & Ethical Data Collection Platform",
    description=(
        "Production-grade, 100% free multi-agent interview question and coding problem indexing platform. "
        "Powered by 14 specialized agents, local NVIDIA Nemotron AI inference, and PostgreSQL/pgvector."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration for Streamlit & local clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Prometheus /metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Include API routes
app.include_router(router)

# Mount Web Frontend Static Files
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

