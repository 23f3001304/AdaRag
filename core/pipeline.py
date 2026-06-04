"""Pipeline orchestration: the ingest and answer services, with injected collaborators."""

from __future__ import annotations

import uuid

from chunking.base import Chunk, Chunker
from core.db import Database
from core.interfaces import EmbeddingProvider, LLMProvider
from core.models import Chunk as ChunkRow
from core.models import Document
from enrichment.contextual import ContextualEnricher
from enrichment.metadata import ChunkMetadata, MetadataEnricher
from index.qdrant_hybrid import QdrantIndex
from rerank.base import Reranker
from retrieval.hybrid import HybridRetriever
from retrieval.query_rewrite import QueryRewriter


class IngestService:
    """Chunk -> optional enrich -> embed (dense+sparse) -> store in Qdrant + Postgres."""

    def __init__(
        self,
        chunker: Chunker,
        embedder: EmbeddingProvider,
        index: QdrantIndex,
        db: Database,
        enricher: ContextualEnricher | None = None,
        metadata: MetadataEnricher | None = None,
    ) -> None:
        self._chunker = chunker
        self._embedder = embedder
        self._index = index
        self._db = db
        self._enricher = enricher
        self._metadata = metadata

    async def ingest(self, source: str, text: str) -> dict:
        chunks = self._chunker.chunk(text)
        if not chunks:
            raise ValueError("document produced no chunks (empty after stripping)")
        contexts = await self._contexts(chunks, text)
        metas = await self._metadata_for(chunks)
        to_embed = [
            self._embed_text(ctx, c.text, m.sparse_terms())
            for ctx, c, m in zip(contexts, chunks, metas, strict=True)
        ]
        dense, sparse = await self._embedder.embed_hybrid(to_embed)
        await self._index.ensure(self._embedder.dim)
        doc_id = str(uuid.uuid4())
        ids = [str(uuid.uuid4()) for _ in chunks]
        points = []
        for cid, d, s, c, ctx, m in zip(ids, dense, sparse, chunks, contexts, metas, strict=True):
            payload = {
                "doc_id": doc_id,
                "source": source,
                "position": c.index,
                "text": c.text,
                "context": ctx,
                "entities": m.entities,
                "dates": m.dates,
            }
            points.append(self._index.point(cid, d, s, payload))
        await self._index.upsert(points)
        async with self._db.session() as session:
            session.add(Document(id=doc_id, source=source, modality="text"))
            session.add_all(
                ChunkRow(id=cid, document_id=doc_id, position=c.index, text=c.text)
                for cid, c in zip(ids, chunks, strict=True)
            )
            await session.commit()
        return {"document_id": doc_id, "chunks": len(chunks), "source": source}

    async def _contexts(self, chunks: list[Chunk], document: str) -> list[str]:
        """One situating context per chunk (empty when disabled, or when a single call fails)."""
        if self._enricher is None:
            return ["" for _ in chunks]
        out: list[str] = []
        for c in chunks:
            try:
                out.append(await self._enricher.context_for(c.text, document))
            except Exception:  # a flaky enrichment call shouldn't abort a whole ingest
                out.append("")
        return out

    async def _metadata_for(self, chunks: list[Chunk]) -> list[ChunkMetadata]:
        """One ChunkMetadata per chunk (empty when metadata enrichment is disabled)."""
        if self._metadata is None:
            return [ChunkMetadata() for _ in chunks]
        return [await self._metadata.extract(c.text) for c in chunks]

    @staticmethod
    def _embed_text(context: str, text: str, terms: str) -> str:
        """Assemble the text to embed: situating context, the chunk, then its salient terms."""
        return "\n\n".join(p for p in (context, text, terms) if p)


_ANSWER_PROMPT = """Answer the question using only the context below. Cite sources inline as [n].
If the context does not contain the answer, say you don't know.

Context:
{context}

Question: {query}

Answer:"""


class AnswerService:
    """Retrieve candidates, rerank them, and generate a cited answer from the top_k."""

    def __init__(
        self,
        retriever: HybridRetriever,
        reranker: Reranker,
        llm: LLMProvider,
        top_k: int,
        rewriter: QueryRewriter | None = None,
    ) -> None:
        self._retriever = retriever
        self._reranker = reranker
        self._llm = llm
        self._top_k = top_k
        self._rewriter = rewriter

    async def answer(self, query: str) -> dict:
        search = await self._rewriter.rewrite(query) if self._rewriter else query
        candidates = await self._retriever.retrieve(search)
        hits = await self._reranker.rerank(query, candidates, self._top_k)
        if not hits:
            return {"answer": "No documents have been ingested yet.", "citations": []}
        context = "\n\n".join(f"[{i + 1}] ({h.source}) {h.text}" for i, h in enumerate(hits))
        answer = await self._llm.generate(_ANSWER_PROMPT.format(context=context, query=query))
        citations = [
            {"n": i + 1, "source": h.source, "chunk_id": h.chunk_id, "score": round(h.score, 4)}
            for i, h in enumerate(hits)
        ]
        return {"answer": answer.strip(), "citations": citations}
