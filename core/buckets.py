"""RAG buckets: multiple isolated pipelines in one deployment, each its own Qdrant collection.

A bucket scopes ingest, retrieval, and chat to its own corpus, so a user runs several independent
RAG pipelines at once. The heavy stateless collaborators (embedder, reranker, LLM, chunker) are
built once and shared; only the index (and its bound services) are per-bucket and cached. The
"default" bucket maps to the base collection so existing single-corpus behavior is unchanged.
"""

from __future__ import annotations

import re

from chunking.registry import build_chunker
from core.config import Settings
from core.db import Database
from core.pipeline import AnswerService, IngestService
from enrichment.contextual import ContextualEnricher
from enrichment.metadata import MetadataEnricher
from index.qdrant_hybrid import QdrantIndex
from orchestrator.chat import ChatOrchestrator
from providers.factory import ProviderFactory
from rerank.cross_encoder import CrossEncoderReranker
from retrieval.hybrid import HybridRetriever
from retrieval.query_rewrite import HydeTransformer, QueryRewriter

DEFAULT_BUCKET = "default"


def bucket_slug(name: str) -> str:
    """Normalize a bucket name to a safe collection suffix ([a-z0-9_]); raises if empty."""
    slug = re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")
    if not slug:
        raise ValueError(f"invalid bucket name: {name!r} (needs a letter or digit)")
    return slug


def collection_name(base: str, bucket: str) -> str:
    """The Qdrant collection for a bucket; the default bucket keeps the base collection name."""
    return base if bucket == DEFAULT_BUCKET else f"{base}_{bucket_slug(bucket)}"


class BucketServices:
    """The pipeline trio for one bucket, all bound to the same collection."""

    def __init__(
        self, ingest: IngestService, answer: AnswerService, chat: ChatOrchestrator
    ) -> None:
        self.ingest = ingest
        self.answer = answer
        self.chat = chat


class BucketManager:
    """Builds and caches per-bucket services; shared models are constructed once here."""

    def __init__(
        self, qdrant, db: Database, settings: Settings, providers: ProviderFactory
    ) -> None:
        self._qdrant = qdrant
        self._db = db
        self._s = settings
        self._embedder = providers.embeddings()
        self._llm = providers.llm()
        self._reranker = CrossEncoderReranker(settings.rerank_model)
        self._chunker = build_chunker(
            settings.chunk_size, settings.chunk_overlap, settings.adaptive_chunking
        )
        self._enricher = ContextualEnricher(self._llm) if settings.enrich_context else None
        self._metadata = MetadataEnricher(self._llm) if settings.enrich_metadata else None
        self._transform: HydeTransformer | QueryRewriter | None = None
        if settings.hyde:
            self._transform = HydeTransformer(self._llm)
        elif settings.rewrite_query:
            self._transform = QueryRewriter(self._llm)
        self._query_meta = MetadataEnricher(self._llm) if settings.metadata_filter else None
        self._cache: dict[str, BucketServices] = {}

    def _index(self, bucket: str) -> QdrantIndex:
        return QdrantIndex(self._qdrant, collection_name(self._s.qdrant_collection, bucket))

    def services(self, bucket: str) -> BucketServices:
        """Get (or build) the cached ingest/answer/chat services scoped to this bucket."""
        if bucket not in self._cache:
            index = self._index(bucket)
            retriever = HybridRetriever(self._embedder, index, self._s.rerank_candidates)
            ingest = IngestService(
                self._chunker, self._embedder, index, self._db, self._enricher, self._metadata
            )
            answer = AnswerService(
                retriever,
                self._reranker,
                self._llm,
                self._s.top_k,
                self._transform,
                self._query_meta,
            )
            chat = ChatOrchestrator(answer, self._llm)
            self._cache[bucket] = BucketServices(ingest, answer, chat)
        return self._cache[bucket]

    async def create(self, bucket: str) -> str:
        """Pre-create a bucket's collection (ingest also auto-creates); returns the slug."""
        await self._index(bucket).ensure(self._embedder.dim)
        return bucket_slug(bucket) if bucket != DEFAULT_BUCKET else DEFAULT_BUCKET

    async def delete(self, bucket: str) -> None:
        """Drop a bucket's collection and evict its cached services (the default is protected)."""
        if bucket == DEFAULT_BUCKET:
            raise ValueError("the default bucket cannot be deleted")
        await self._qdrant.delete_collection(collection_name(self._s.qdrant_collection, bucket))
        self._cache.pop(bucket, None)

    async def list_buckets(self) -> list[str]:
        """All buckets that have a collection, by name (the base collection shows as 'default')."""
        base = self._s.qdrant_collection
        prefix = f"{base}_"
        names = []
        for col in (await self._qdrant.get_collections()).collections:
            if col.name == base:
                names.append(DEFAULT_BUCKET)
            elif col.name.startswith(prefix):
                names.append(col.name[len(prefix):])
        return sorted(names)
