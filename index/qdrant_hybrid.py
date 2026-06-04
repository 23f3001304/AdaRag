"""Qdrant collection management + dense upsert/search (named-vector ready for Phase 1 sparse)."""

from __future__ import annotations

from qdrant_client import AsyncQdrantClient, models

DENSE = "dense"  # named vector; a "sparse" vector joins it in Phase 1 (hybrid)


async def ensure_collection(client: AsyncQdrantClient, name: str, dim: int) -> None:
    """Create the collection with a named dense vector if it doesn't already exist."""
    if await client.collection_exists(name):
        return
    await client.create_collection(
        collection_name=name,
        vectors_config={DENSE: models.VectorParams(size=dim, distance=models.Distance.COSINE)},
    )


def make_point(point_id: str, vector: list[float], payload: dict) -> models.PointStruct:
    """Build a Qdrant point under the named dense vector."""
    return models.PointStruct(id=point_id, vector={DENSE: vector}, payload=payload)


async def upsert_chunks(client: AsyncQdrantClient, name: str, points: list[models.PointStruct]) -> None:
    """Upsert points into the collection."""
    if points:
        await client.upsert(collection_name=name, points=points)


async def search_dense(client: AsyncQdrantClient, name: str, vector: list[float], top_k: int):
    """Dense nearest-neighbour search; returns scored points with their payloads."""
    result = await client.query_points(
        collection_name=name, query=vector, using=DENSE, limit=top_k, with_payload=True
    )
    return result.points
