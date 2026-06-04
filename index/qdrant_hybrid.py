"""Qdrant index: one collection with named dense + sparse vectors, and hybrid RRF search."""

from __future__ import annotations

from qdrant_client import AsyncQdrantClient, models

DENSE = "dense"
SPARSE = "sparse"


def _sparse(sparse: dict[int, float]) -> models.SparseVector:
    return models.SparseVector(indices=list(sparse.keys()), values=list(sparse.values()))


class QdrantIndex:
    """Owns one Qdrant collection: ensures its schema, upserts points, and searches it."""

    def __init__(self, client: AsyncQdrantClient, collection: str) -> None:
        self._client = client
        self._collection = collection

    async def ensure(self, dim: int) -> None:
        """Create the collection (named dense + sparse vectors) if it doesn't exist."""
        if await self._client.collection_exists(self._collection):
            return
        await self._client.create_collection(
            collection_name=self._collection,
            vectors_config={DENSE: models.VectorParams(size=dim, distance=models.Distance.COSINE)},
            sparse_vectors_config={SPARSE: models.SparseVectorParams()},
        )

    @staticmethod
    def point(
        point_id: str, dense: list[float], sparse: dict[int, float], payload: dict
    ) -> models.PointStruct:
        """Build a point carrying both the dense and sparse vectors."""
        return models.PointStruct(
            id=point_id, vector={DENSE: dense, SPARSE: _sparse(sparse)}, payload=payload
        )

    async def upsert(self, points: list[models.PointStruct]) -> None:
        """Upsert points into the collection."""
        if points:
            await self._client.upsert(collection_name=self._collection, points=points)

    async def search(self, dense: list[float], sparse: dict[int, float], top_k: int):
        """Fetch dense + sparse candidates and fuse them server-side with RRF."""
        result = await self._client.query_points(
            collection_name=self._collection,
            prefetch=[
                models.Prefetch(query=dense, using=DENSE, limit=top_k),
                models.Prefetch(query=_sparse(sparse), using=SPARSE, limit=top_k),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=top_k,
            with_payload=True,
        )
        return result.points
