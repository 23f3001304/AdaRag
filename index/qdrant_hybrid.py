"""Qdrant index: one collection with named dense + sparse vectors, and hybrid RRF search."""

from __future__ import annotations

from qdrant_client import AsyncQdrantClient, models

DENSE = "dense"
SPARSE = "sparse"


def _sparse(sparse: dict[int, float]) -> models.SparseVector:
    return models.SparseVector(indices=list(sparse.keys()), values=list(sparse.values()))


def entity_filter(entities: list[str]) -> models.Filter | None:
    """Filter for chunks whose stored entities overlap `entities` (None when the list is empty)."""
    if not entities:
        return None
    return models.Filter(
        must=[models.FieldCondition(key="entities", match=models.MatchAny(any=entities))]
    )


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
        """Upsert points into the collection (wait=True so they're immediately listable)."""
        if points:
            await self._client.upsert(collection_name=self._collection, points=points, wait=True)

    async def fetch_doc(self, doc_id: str) -> list[tuple[str, dict]]:
        """Every (point_id, payload) for a document's chunks - used to re-tag and re-embed them."""
        flt = models.Filter(
            must=[models.FieldCondition(key="doc_id", match=models.MatchValue(value=doc_id))]
        )
        out: list[tuple[str, dict]] = []
        offset = None
        while True:
            points, offset = await self._client.scroll(
                collection_name=self._collection,
                scroll_filter=flt,
                limit=256,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            out.extend((str(p.id), p.payload or {}) for p in points)
            if offset is None:
                return out

    async def distinct_entities(self) -> list[str]:
        """Distinct entity names across the collection (candidate answers for a clarification)."""
        seen: dict[str, None] = {}
        offset = None
        while True:
            try:
                points, offset = await self._client.scroll(
                    collection_name=self._collection,
                    limit=256,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False,
                )
            except Exception:
                return list(seen)  # collection may not exist yet
            for p in points:
                for entity in (p.payload or {}).get("entities") or []:
                    seen.setdefault(str(entity), None)
            if offset is None:
                return list(seen)

    async def search(
        self,
        dense: list[float],
        sparse: dict[int, float],
        top_k: int,
        query_filter: models.Filter | None = None,
    ):
        """Fetch dense + sparse candidates, RRF-fuse server-side, optionally payload-filtered."""
        result = await self._client.query_points(
            collection_name=self._collection,
            prefetch=[
                models.Prefetch(query=dense, using=DENSE, limit=top_k, filter=query_filter),
                models.Prefetch(
                    query=_sparse(sparse), using=SPARSE, limit=top_k, filter=query_filter
                ),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=top_k,
            with_payload=True,
        )
        return result.points
