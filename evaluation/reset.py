"""Reset the corpus stores to empty — shared by the eval scripts for a clean slate."""

from __future__ import annotations

from qdrant_client import AsyncQdrantClient
from sqlalchemy import text

from core.db import Database


async def reset_corpus(qdrant: AsyncQdrantClient, db: Database, collection: str) -> None:
    """Drop the Qdrant collection and truncate the Postgres corpus tables (best-effort)."""
    try:
        await qdrant.delete_collection(collection)
    except Exception:  # best-effort: the collection may not exist yet
        pass
    async with db.session() as session:
        await session.execute(text("TRUNCATE documents, chunks, eval_questions CASCADE"))
        await session.commit()
