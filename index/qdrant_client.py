"""Qdrant access: async client factory and a health probe."""

from __future__ import annotations

from qdrant_client import AsyncQdrantClient


def create_qdrant(url: str) -> AsyncQdrantClient:
    """Build the async Qdrant client from a base URL (e.g. http://localhost:6333)."""
    return AsyncQdrantClient(url=url)


async def ping_qdrant(client: AsyncQdrantClient) -> bool:
    """True if Qdrant answers. A health probe reports status, it never raises."""
    try:
        await client.get_collections()
        return True
    except Exception:
        return False
