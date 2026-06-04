"""Postgres access: async engine factory and a health probe."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


def create_engine(database_url: str) -> AsyncEngine:
    """Build the async engine. pool_pre_ping avoids handing out dead connections."""
    return create_async_engine(database_url, pool_pre_ping=True)


async def ping_db(engine: AsyncEngine) -> bool:
    """True if a trivial query succeeds. A health probe reports status, it never raises."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
