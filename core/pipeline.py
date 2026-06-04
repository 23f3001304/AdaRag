"""Pipeline orchestration: the ingest and answer services, with injected collaborators."""

from __future__ import annotations

import uuid

from chunking.base import Chunker
from core.db import Database
from core.interfaces import EmbeddingProvider, LLMProvider
from core.models import Chunk as ChunkRow
from core.models import Document
from index.qdrant_hybrid import QdrantIndex
from retrieval.hybrid import HybridRetriever


class IngestService:
    """Chunk -> embed (dense + sparse) -> store in Qdrant + Postgres."""

    def __init__(
        self, chunker: Chunker, embedder: EmbeddingProvider, index: QdrantIndex, db: Database
    ) -> None:
        self._chunker = chunker
        self._embedder = embedder
        self._index = index
        self._db = db

    async def ingest(self, source: str, text: str) -> dict:
        chunks = self._chunker.chunk(text)
        if not chunks:
            raise ValueError("document produced no chunks (empty after stripping)")
        dense, sparse = await self._embedder.embed_hybrid([c.text for c in chunks])
        await self._index.ensure(self._embedder.dim)
        doc_id = str(uuid.uuid4())
        ids = [str(uuid.uuid4()) for _ in chunks]
        points = [
            self._index.point(
                cid, d, s, {"doc_id": doc_id, "source": source, "position": c.index, "text": c.text}
            )
            for cid, d, s, c in zip(ids, dense, sparse, chunks, strict=True)
        ]
        await self._index.upsert(points)
        async with self._db.session() as session:
            session.add(Document(id=doc_id, source=source, modality="text"))
            session.add_all(
                ChunkRow(id=cid, document_id=doc_id, position=c.index, text=c.text)
                for cid, c in zip(ids, chunks, strict=True)
            )
            await session.commit()
        return {"document_id": doc_id, "chunks": len(chunks), "source": source}


_ANSWER_PROMPT = """Answer the question using only the context below. Cite sources inline as [n].
If the context does not contain the answer, say you don't know.

Context:
{context}

Question: {query}

Answer:"""


class AnswerService:
    """Retrieve the top-k chunks and generate a cited answer."""

    def __init__(self, retriever: HybridRetriever, llm: LLMProvider) -> None:
        self._retriever = retriever
        self._llm = llm

    async def answer(self, query: str) -> dict:
        hits = await self._retriever.retrieve(query)
        if not hits:
            return {"answer": "No documents have been ingested yet.", "citations": []}
        context = "\n\n".join(f"[{i + 1}] ({h.source}) {h.text}" for i, h in enumerate(hits))
        answer = await self._llm.generate(_ANSWER_PROMPT.format(context=context, query=query))
        citations = [
            {"n": i + 1, "source": h.source, "chunk_id": h.chunk_id, "score": round(h.score, 4)}
            for i, h in enumerate(hits)
        ]
        return {"answer": answer.strip(), "citations": citations}
