"""Async database engine and session management."""

from __future__ import annotations

from typing import AsyncGenerator

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings


engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
)

AsyncSessionMaker = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)

# Alias for use in Celery tasks (non-request context)
AsyncSessionLocal = AsyncSessionMaker


async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async DB session.

    Also sets app.current_user_id for PostgreSQL RLS policies when available.
    """
    current_user_id: str | None = getattr(request.state, "user_id", None)

    async with AsyncSessionMaker() as session:
        try:
            if current_user_id:
                await session.execute(
                    text("SELECT set_config('app.current_user_id', :uid, TRUE)"),
                    {"uid": str(current_user_id)},
                )
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            # Clear RLS context before closing. Guard against a failed session
            # so the cleanup execute doesn't raise PendingRollbackError.
            if current_user_id:
                try:
                    await session.execute(
                        text("SELECT set_config('app.current_user_id', '', TRUE)"),
                    )
                except Exception:
                    pass
            await session.close()

