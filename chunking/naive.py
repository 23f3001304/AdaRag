"""Naive fixed-size chunking — the Phase 0 baseline strategy (Phase 3 adds structure-aware ones)."""

from __future__ import annotations

from chunking.base import Chunk


class NaiveChunker:
    """Fixed-size character windows with overlap. Ignores structure (sentences, sections)."""

    def __init__(self, size: int, overlap: int) -> None:
        if size <= 0:
            raise ValueError(f"size must be positive, got {size}")
        if not 0 <= overlap < size:
            raise ValueError(f"overlap must be in [0, size), got {overlap}")
        self._size = size
        self._overlap = overlap

    def chunk(self, text: str) -> list[Chunk]:
        """Split text into fixed-size windows overlapping by ``overlap`` characters."""
        if not text.strip():
            return []
        step = self._size - self._overlap
        chunks: list[Chunk] = []
        start = 0
        while start < len(text):
            end = min(start + self._size, len(text))
            window = text[start:end]
            if window.strip():
                chunks.append(Chunk(len(chunks), window, start, end))
            if end == len(text):
                break
            start += step
        return chunks
