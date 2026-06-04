"""Postgres access: an async engine wrapper with sessions, table setup, and a health probe."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from core.models import Base


class Database:
    """Owns the async engine; hands out sessions, creates tables, and probes health."""

    def __init__(self, url: str) -> None:
        self._engine = create_async_engine(url, pool_pre_ping=True)

    def session(self) -> AsyncSession:
        """A new async session bound to the engine."""
        return AsyncSession(self._engine)

    async def create_all(self) -> None:
        """Create tables if missing (Phase 0; Alembic migrations once the schema settles)."""
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def ping(self) -> bool:
        """True if a trivial query succeeds. A health probe reports status, it never raises."""
        try:
            async with self._engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    async def dispose(self) -> None:
        await self._engine.dispose()
