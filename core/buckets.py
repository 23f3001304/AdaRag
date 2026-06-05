"""RAG buckets: multiple isolated pipelines in one deployment, each its own Qdrant collection.

A bucket scopes ingest, retrieval, and chat to its own corpus, so a user runs several independent
RAG pipelines at once. The heavy stateless collaborators (embedder, reranker, LLM, chunker) are
built once and shared; only the index (and its bound services) are per-bucket and cached. The
"default" bucket maps to the base collection so existing single-corpus behavior is unchanged.
"""

from __future__ import annotations

import contextlib
import re
from pathlib import Path

from qdrant_client import models
from sqlalchemy import delete as sa_delete

from chunking.registry import build_chunker
from core.config import Settings
from core.db import Database
from core.interfaces import EmbeddingProvider, LLMProvider
from core.models import Document
from core.pipeline import AnswerService, IngestService
from enrichment.contextual import ContextualEnricher
from enrichment.metadata import MetadataEnricher
from index.qdrant_hybrid import QdrantIndex
from orchestrator.chat import ChatOrchestrator
from providers.factory import ProviderFactory
from providers.registry import build_llm
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


_UPLOADS = Path("data/uploads")


def _is_upload(path: str) -> bool:
    """True only for files under data/uploads (a bucket's own uploads, safe to remove)."""
    try:
        return _UPLOADS.resolve() in Path(path).resolve().parents
    except OSError:
        return False


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

    @property
    def llm(self) -> LLMProvider:
        """The shared LLM (reused for bucket-independent tasks like chat intent routing)."""
        return self._llm

    @property
    def embedder(self) -> EmbeddingProvider:
        """The shared embedder (reused by the optimizer to score a bucket's retrieval)."""
        return self._embedder

    @property
    def reranker(self) -> CrossEncoderReranker:
        """The shared cross-encoder reranker (reused by the optimizer)."""
        return self._reranker

    def llm_for(self, provider: str, model: str) -> LLMProvider:
        """Build an LLM for a specific provider+model (per-request chat model switching).

        Under cli-bridge the choice is routed to the host bridge; otherwise it's built directly.
        """
        if self._s.llm_provider == "cli-bridge":
            from providers.http_bridge import HttpBridgeLLM

            return HttpBridgeLLM(self._s.cli_bridge_url, model, provider)
        return build_llm(self._s.model_copy(update={"llm_provider": provider, "llm_model": model}))

    async def available_modes(self) -> list[dict]:
        """The provider+model combos available to switch between (from the bridge, if used)."""
        if self._s.llm_provider == "cli-bridge":
            from providers.http_bridge import bridge_models

            with contextlib.suppress(Exception):
                return await bridge_models(self._s.cli_bridge_url)
            return []
        return [{"provider": self._s.llm_provider, "model": self._s.llm_model}]

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
        """Delete a bucket fully: its Qdrant collection, uploaded originals, and Postgres rows."""
        if bucket == DEFAULT_BUCKET:
            raise ValueError("the default bucket cannot be deleted")
        collection = collection_name(self._s.qdrant_collection, bucket)
        doc_ids, paths = await self._scan(collection)
        for path in paths:
            if _is_upload(path):
                with contextlib.suppress(OSError):
                    Path(path).unlink(missing_ok=True)
        if doc_ids:
            async with self._db.session() as session:
                await session.execute(sa_delete(Document).where(Document.id.in_(doc_ids)))
                await session.commit()
        await self._qdrant.delete_collection(collection)
        self._cache.pop(bucket, None)

    async def delete_document(self, bucket: str, source: str) -> None:
        """Delete one source file from a bucket: its Qdrant points, Postgres rows, and upload."""
        collection = collection_name(self._s.qdrant_collection, bucket)
        flt = models.Filter(
            must=[models.FieldCondition(key="source", match=models.MatchValue(value=source))]
        )
        doc_ids, paths = await self._scan(collection, flt)
        for path in paths:
            if _is_upload(path):
                with contextlib.suppress(OSError):
                    Path(path).unlink(missing_ok=True)
        if doc_ids:
            async with self._db.session() as session:
                await session.execute(sa_delete(Document).where(Document.id.in_(doc_ids)))
                await session.commit()
        with contextlib.suppress(Exception):
            await self._qdrant.delete(
                collection_name=collection, points_selector=models.FilterSelector(filter=flt)
            )

    async def _scan(
        self, collection: str, scroll_filter: models.Filter | None = None
    ) -> tuple[set[str], set[str]]:
        """Collect doc_ids + original file paths from a collection's chunks (empty if missing)."""
        doc_ids: set[str] = set()
        paths: set[str] = set()
        offset = None
        while True:
            try:
                points, offset = await self._qdrant.scroll(
                    collection_name=collection,
                    limit=256,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False,
                    scroll_filter=scroll_filter,
                )
            except Exception:
                break
            for point in points:
                payload = point.payload or {}
                if payload.get("doc_id"):
                    doc_ids.add(str(payload["doc_id"]))
                if payload.get("original_path"):
                    paths.add(str(payload["original_path"]))
            if offset is None:
                break
        return doc_ids, paths

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

    async def documents(self, bucket: str) -> list[dict]:
        """Aggregate a bucket's indexed chunks by source - one row per ingested file."""
        collection = collection_name(self._s.qdrant_collection, bucket)
        agg: dict[str, dict] = {}
        offset = None
        while True:
            try:
                points, offset = await self._qdrant.scroll(
                    collection_name=collection,
                    limit=256,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False,
                )
            except Exception:
                break  # the collection may not exist yet
            for point in points:
                payload = point.payload or {}
                source = str(payload.get("source", "unknown"))
                row = agg.setdefault(
                    source,
                    {
                        "source": source,
                        "modality": payload.get("modality", "text"),
                        "original_path": payload.get("original_path"),
                        "chunks": 0,
                    },
                )
                row["chunks"] += 1
            if offset is None:
                break
        rows = sorted(agg.values(), key=lambda r: r["source"])
        for row in rows:
            path = row.get("original_path")
            row["original_exists"] = bool(path) and _is_upload(path) and Path(path).exists()
        return rows
