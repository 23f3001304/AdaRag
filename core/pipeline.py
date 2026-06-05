"""Pipeline orchestration: the ingest and answer services, with injected collaborators."""

from __future__ import annotations

import asyncio
import uuid

from chunking.base import Chunk, Chunker
from core.db import Database
from core.interfaces import EmbeddingProvider, LLMProvider
from core.models import Chunk as ChunkRow
from core.models import Document
from enrichment.contextual import ContextualEnricher
from enrichment.metadata import ChunkMetadata, MetadataEnricher
from index.qdrant_hybrid import QdrantIndex, entity_filter
from rerank.base import Reranker
from retrieval.hybrid import HybridRetriever
from retrieval.query_rewrite import QueryTransformer

_ENRICH_CONCURRENCY = 6  # parallel enrichment LLM calls per ingest (bounds concurrent CLI procs)


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

    async def ingest(
        self, source: str, text: str, modality: str = "text", original_path: str | None = None
    ) -> dict:
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
                "modality": modality,
                "original_path": original_path,
            }
            points.append(self._index.point(cid, d, s, payload))
        await self._index.upsert(points)
        async with self._db.session() as session:
            session.add(Document(id=doc_id, source=source, modality=modality))
            session.add_all(
                ChunkRow(id=cid, document_id=doc_id, position=c.index, text=c.text)
                for cid, c in zip(ids, chunks, strict=True)
            )
            await session.commit()
        return {"document_id": doc_id, "chunks": len(chunks), "source": source}

    async def _contexts(self, chunks: list[Chunk], document: str) -> list[str]:
        """One situating context per chunk, enriched concurrently (empty when off or on failure)."""
        if self._enricher is None:
            return ["" for _ in chunks]
        sem = asyncio.Semaphore(_ENRICH_CONCURRENCY)

        async def one(chunk: Chunk) -> str:
            async with sem:
                try:
                    return await self._enricher.context_for(chunk.text, document)
                except Exception:  # a flaky enrichment call shouldn't abort the whole ingest
                    return ""

        return list(await asyncio.gather(*(one(c) for c in chunks)))

    async def _metadata_for(self, chunks: list[Chunk]) -> list[ChunkMetadata]:
        """One ChunkMetadata per chunk, extracted concurrently (empty when disabled)."""
        if self._metadata is None:
            return [ChunkMetadata() for _ in chunks]
        sem = asyncio.Semaphore(_ENRICH_CONCURRENCY)

        async def one(chunk: Chunk) -> ChunkMetadata:
            async with sem:
                try:
                    return await self._metadata.extract(chunk.text)
                except Exception:
                    return ChunkMetadata()

        return list(await asyncio.gather(*(one(c) for c in chunks)))

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

_REASON_PROMPT = """In 2-3 short sentences, explain how you reached this answer from the sources
(which mattered, what you inferred). Be concise and do not repeat the answer.

Question: {query}
Answer: {answer}

Reasoning:"""


async def _answer_with_thinking(gen: LLMProvider, prompt: str, query: str) -> tuple[str, str]:
    """Return (answer, thinking): the model's native reasoning if exposed, else a post-hoc trace."""
    native = None
    if hasattr(gen, "generate_thinking"):
        answer, native = await gen.generate_thinking(prompt)
    else:
        answer = await gen.generate(prompt)
    if native:
        return answer, native
    reason = (await gen.generate(_REASON_PROMPT.format(query=query, answer=answer))).strip()
    return answer, reason


class AnswerService:
    """Retrieve candidates, rerank them, and generate a cited answer from the top_k."""

    def __init__(
        self,
        retriever: HybridRetriever,
        reranker: Reranker,
        llm: LLMProvider,
        top_k: int,
        transform: QueryTransformer | None = None,
        query_meta: MetadataEnricher | None = None,
    ) -> None:
        self._retriever = retriever
        self._reranker = reranker
        self._llm = llm
        self._top_k = top_k
        self._transform = transform
        self._query_meta = query_meta

    async def answer(
        self,
        query: str,
        *,
        persona: str | None = None,
        top_k: int | None = None,
        llm: LLMProvider | None = None,
        thinking: bool = False,
    ) -> dict:
        """Answer a query; a skill may override persona/top_k and a mode may override the LLM."""
        search = await self._transform.transform(query) if self._transform else query
        qfilter = None
        if self._query_meta is not None:
            qfilter = entity_filter((await self._query_meta.extract(query)).entities)
        candidates = await self._retriever.retrieve(search, qfilter)
        if qfilter is not None and not candidates:
            candidates = await self._retriever.retrieve(search)  # filter too strict; fall back
        k = top_k if top_k and top_k > 0 else self._top_k
        hits = await self._reranker.rerank(query, candidates, k)
        if not hits:
            return {
                "answer": "No documents have been ingested yet.",
                "citations": [],
                "thinking": None,
            }
        context = "\n\n".join(f"[{i + 1}] ({h.source}) {h.text}" for i, h in enumerate(hits))
        prompt = _ANSWER_PROMPT.format(context=context, query=query)
        if persona and persona.strip():
            prompt = f"{persona.strip()}\n\n{prompt}"
        gen = llm or self._llm
        if thinking:
            answer, think = await _answer_with_thinking(gen, prompt, query)
        else:
            answer, think = await gen.generate(prompt), None
        citations = [
            {
                "n": i + 1,
                "source": h.source,
                "chunk_id": h.chunk_id,
                "score": round(h.score, 4),
                "modality": h.modality,
                "original_path": h.original_path,
            }
            for i, h in enumerate(hits)
        ]
        return {"answer": answer.strip(), "citations": citations, "thinking": think}
