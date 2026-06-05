"""Weave a chosen entity name into a document's chunks so retrieval links the file to that person.

Run when a user answers an ingest clarification ("this photo is John"): the name is prepended to
each chunk's situating context (which is embedded and reranked) and added to its entities (the
metadata filter), then the chunk is re-embedded. Two people's photos become distinguishable.
"""

from __future__ import annotations

from core.interfaces import EmbeddingProvider
from index.qdrant_hybrid import QdrantIndex


def _embed_text(context: str, text: str, terms: str) -> str:
    """Same assembly as ingest: situating context, the chunk, then its salient terms."""
    return "\n\n".join(p for p in (context, text, terms) if p)


async def retag_document(
    index: QdrantIndex, embedder: EmbeddingProvider, doc_id: str, entity: str
) -> int:
    """Tag every chunk of `doc_id` with `entity` (payload + re-embed); returns chunks updated."""
    chunks = await index.fetch_doc(doc_id)
    if not chunks or not entity.strip():
        return 0
    prefix = f"This is {entity.strip()}."
    ids, payloads, texts = [], [], []
    for cid, payload in chunks:
        entities = list(payload.get("entities") or [])
        if entity not in entities:
            entities.append(entity)
        context = f"{prefix} {payload.get('context', '')}".strip()
        ids.append(cid)
        payloads.append({**payload, "context": context, "entities": entities})
        texts.append(_embed_text(context, payload.get("text", ""), " ".join(entities)))
    dense, sparse = await embedder.embed_hybrid(texts)
    points = [
        index.point(cid, d, s, pl)
        for cid, d, s, pl in zip(ids, dense, sparse, payloads, strict=True)
    ]
    await index.upsert(points)
    return len(points)
