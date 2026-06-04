"""Ingestion pipeline: text -> naive chunks -> embeddings -> Qdrant + Postgres."""

from __future__ import annotations

import uuid

from qdrant_client import AsyncQdrantClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from chunking.naive import naive_chunks
from core.config import Settings
from core.interfaces import EmbeddingProvider, LLMProvider
from core.models import Chunk as ChunkRow
from core.models import Document
from index.qdrant_hybrid import ensure_collection, make_point, upsert_chunks
from retrieval.hybrid import retrieve


async def ingest_text(
    *,
    source: str,
    text: str,
    settings: Settings,
    embedder: EmbeddingProvider,
    qdrant: AsyncQdrantClient,
    engine: AsyncEngine,
) -> dict:
    """Chunk, embed, and store one text document. Returns a small summary."""
    chunks = naive_chunks(text, settings.chunk_size, settings.chunk_overlap)
    if not chunks:
        raise ValueError("document produced no chunks (empty after stripping)")

    dense, sparse = await embedder.embed_hybrid([c.text for c in chunks])

    await ensure_collection(qdrant, settings.qdrant_collection, embedder.dim)
    doc_id = str(uuid.uuid4())
    chunk_ids = [str(uuid.uuid4()) for _ in chunks]
    points = [
        make_point(cid, d, s, {"doc_id": doc_id, "source": source, "position": c.index, "text": c.text})
        for cid, d, s, c in zip(chunk_ids, dense, sparse, chunks)
    ]
    await upsert_chunks(qdrant, settings.qdrant_collection, points)

    async with AsyncSession(engine) as session:
        session.add(Document(id=doc_id, source=source, modality="text"))
        session.add_all(
            ChunkRow(id=cid, document_id=doc_id, position=c.index, text=c.text)
            for cid, c in zip(chunk_ids, chunks)
        )
        await session.commit()

    return {"document_id": doc_id, "chunks": len(chunks), "source": source}


_ANSWER_PROMPT = """Answer the question using only the context below. Cite sources inline as [n].
If the context does not contain the answer, say you don't know.

Context:
{context}

Question: {query}

Answer:"""


async def answer_query(
    *,
    query: str,
    settings: Settings,
    embedder: EmbeddingProvider,
    llm: LLMProvider,
    qdrant: AsyncQdrantClient,
) -> dict:
    """Retrieve the top-k chunks and generate a cited answer."""
    hits = await retrieve(
        query,
        embedder=embedder,
        qdrant=qdrant,
        collection=settings.qdrant_collection,
        top_k=settings.top_k,
    )
    if not hits:
        return {"answer": "No documents have been ingested yet.", "citations": []}
    context = "\n\n".join(f"[{i + 1}] ({h.source}) {h.text}" for i, h in enumerate(hits))
    answer = await llm.generate(_ANSWER_PROMPT.format(context=context, query=query))
    citations = [
        {"n": i + 1, "source": h.source, "chunk_id": h.chunk_id, "score": round(h.score, 4)}
        for i, h in enumerate(hits)
    ]
    return {"answer": answer.strip(), "citations": citations}
