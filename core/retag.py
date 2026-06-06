"""Fold a clarification answer back into a document's chunks so retrieval can use it.

When a user answers an ingest question ("brand? Scott", "who won? Pogacar"), the answer is appended
to every chunk's situating context (embedded + reranked) and, when it is a short term rather than a
sentence, added to the chunk's entities (the metadata filter). Several answers accumulate, so a
photo becomes findable by the rider, the brand, and the event, not just its generic caption.
"""

from __future__ import annotations

from core.interfaces import EmbeddingProvider
from index.qdrant_hybrid import QdrantIndex


def _embed_text(context: str, text: str, terms: str) -> str:
    """Same assembly as ingest: situating context, the chunk, then its salient terms."""
    return "\n\n".join(p for p in (context, text, terms) if p)


async def retag_document(
    index: QdrantIndex, embedder: EmbeddingProvider, doc_id: str, fact: str
) -> int:
    """Append `fact` to each chunk of `doc_id` (context + entities), re-embed; returns count."""
    chunks = await index.fetch_doc(doc_id)
    fact = fact.strip()
    if not chunks or not fact:
        return 0
    is_term = len(fact.split()) <= 4  # a name/brand also joins entities; a sentence is context only
    ids, payloads, texts = [], [], []
    for cid, payload in chunks:
        entities = list(payload.get("entities") or [])
        if is_term and fact not in entities:
            entities.append(fact)
        context = f"{payload.get('context', '')} {fact}".strip()
        # Also prepend the fact to the chunk's text. The answer LLM reads payload.text from each
        # cited hit; context goes into retrieval scoring only. Without this, the rider's name
        # never reaches the model when it summarizes the photo. Skip if already present so a
        # second tag for the same fact doesn't keep stacking.
        text = payload.get("text", "")
        if fact and fact not in text:
            text = (f"This is {fact}. " if is_term else f"{fact}. ") + text
        ids.append(cid)
        payloads.append({**payload, "context": context, "entities": entities, "text": text})
        texts.append(_embed_text(context, text, " ".join(entities)))
    dense, sparse = await embedder.embed_hybrid(texts)
    points = [
        index.point(cid, d, s, pl)
        for cid, d, s, pl in zip(ids, dense, sparse, payloads, strict=True)
    ]
    await index.upsert(points)
    return len(points)
