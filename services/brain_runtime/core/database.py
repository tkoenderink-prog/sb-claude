"""Database connection and session management."""

from contextlib import asynccontextmanager
from functools import lru_cache

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

from .config import get_settings

Base = declarative_base()


@lru_cache()
def get_engine():
    """Get cached async database engine."""
    settings = get_settings()
    # Convert postgresql:// to postgresql+asyncpg://
    db_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
    return create_async_engine(
        db_url,
        echo=settings.debug,
        pool_size=5,
        max_overflow=10,
    )


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get async session factory."""
    return async_sessionmaker(
        get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def get_db() -> AsyncSession:
    """Dependency for getting database session."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database connection pool.

    This function is called during application startup to ensure
    the database connection pool is properly initialized.
    """
    engine = get_engine()
    # Test the connection by executing a simple query
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))


@asynccontextmanager
async def get_session():
    """Context manager for getting a database session outside of FastAPI routes."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
