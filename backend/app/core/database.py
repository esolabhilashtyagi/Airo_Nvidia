from datetime import datetime, timezone
from typing import AsyncGenerator
from sqlalchemy import create_engine
from sqlalchemy.dialects.sqlite.base import DATETIME
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

# Ensure SQLite DateTime results retain timezone information (UTC)
_orig_sqlite_dt_result_processor = DATETIME.result_processor


def _utc_sqlite_dt_result_processor(self, dialect, coltype):
    fn = _orig_sqlite_dt_result_processor(self, dialect, coltype)

    def process(value):
        res = fn(value) if fn else value
        if res is not None and getattr(res, "tzinfo", None) is None:
            return res.replace(tzinfo=timezone.utc)
        return res

    return process


DATETIME.result_processor = _utc_sqlite_dt_result_processor

# Async engine for FastAPI endpoints
async_kwargs = {
    "echo": False,
    "hide_parameters": True,
    "future": True,
}
if "sqlite" not in settings.DATABASE_URL:
    async_kwargs.update({
        "pool_size": 20,
        "max_overflow": 10,
        "pool_pre_ping": True,
    })

async_engine = create_async_engine(
    settings.DATABASE_URL,
    **async_kwargs
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Synchronous engine for Alembic and seed scripts
sync_kwargs = {
    "echo": False,
    "hide_parameters": True,
}
if "sqlite" not in settings.DATABASE_URL_SYNC:
    sync_kwargs.update({
        "pool_size": 10,
        "max_overflow": 5,
        "pool_pre_ping": True,
    })

sync_engine = create_engine(
    settings.DATABASE_URL_SYNC,
    **sync_kwargs
)

SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_sync_db():
    db = SyncSessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
