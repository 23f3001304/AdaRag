"""Naive fixed-size text chunking — the Phase 0 baseline (adaptive chunking arrives in Phase 3)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    """A slice of a document: its text and the character span it came from."""

    index: int
    text: str
    start: int
    end: int


def naive_chunks(text: str, size: int, overlap: int) -> list[Chunk]:
    """Split text into fixed-size character windows overlapping by ``overlap``.

    Naive on purpose: it ignores structure (sentences, sections). Phase 3 replaces this
    with profile-aware chunking; ``size``/``overlap`` become tuned parameters in Phase 5.
    """
    if size <= 0:
        raise ValueError(f"size must be positive, got {size}")
    if not 0 <= overlap < size:
        raise ValueError(f"overlap must be in [0, size), got {overlap}")
    if not text.strip():
        return []

    step = size - overlap
    chunks: list[Chunk] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        window = text[start:end]
        if window.strip():
            chunks.append(Chunk(len(chunks), window, start, end))
        if end == len(text):
            break
        start += step
    return chunks
