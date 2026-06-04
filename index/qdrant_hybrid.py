"""Qdrant collection management + hybrid (dense + sparse) upsert and RRF search."""

from __future__ import annotations

from qdrant_client import AsyncQdrantClient, models

DENSE = "dense"
SPARSE = "sparse"


async def ensure_collection(client: AsyncQdrantClient, name: str, dim: int) -> None:
    """Create the collection with named dense + sparse vectors if it doesn't already exist."""
    if await client.collection_exists(name):
        return
    await client.create_collection(
        collection_name=name,
        vectors_config={DENSE: models.VectorParams(size=dim, distance=models.Distance.COSINE)},
        sparse_vectors_config={SPARSE: models.SparseVectorParams()},
    )


def _sparse(sparse: dict[int, float]) -> models.SparseVector:
    return models.SparseVector(indices=list(sparse.keys()), values=list(sparse.values()))


def make_point(
    point_id: str, dense: list[float], sparse: dict[int, float], payload: dict
) -> models.PointStruct:
    """Build a Qdrant point carrying both the dense and sparse vectors."""
    return models.PointStruct(
        id=point_id, vector={DENSE: dense, SPARSE: _sparse(sparse)}, payload=payload
    )


async def upsert_chunks(client: AsyncQdrantClient, name: str, points: list[models.PointStruct]) -> None:
    """Upsert points into the collection."""
    if points:
        await client.upsert(collection_name=name, points=points)


async def hybrid_search(
    client: AsyncQdrantClient, name: str, dense: list[float], sparse: dict[int, float], top_k: int
):
    """Fetch dense + sparse candidates and fuse them server-side with Reciprocal Rank Fusion."""
    result = await client.query_points(
        collection_name=name,
        prefetch=[
            models.Prefetch(query=dense, using=DENSE, limit=top_k),
            models.Prefetch(query=_sparse(sparse), using=SPARSE, limit=top_k),
        ],
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        limit=top_k,
        with_payload=True,
    )
    return result.points
