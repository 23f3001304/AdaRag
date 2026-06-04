"""Adaptive chunking: profile the document, then delegate to the matching strategy (DESIGN.md)."""

from __future__ import annotations

from chunking.base import Chunk, Chunker
from chunking.profile import DocProfile, DocumentProfiler


class AdaptiveChunker:
    """Routes each document to a profile-specific chunker, falling back to a default strategy.

    Implements the Chunker protocol, so it is a drop-in replacement wherever a chunker is expected.
    """

    def __init__(
        self,
        profiler: DocumentProfiler,
        strategies: dict[DocProfile, Chunker],
        fallback: Chunker,
    ) -> None:
        self._profiler = profiler
        self._strategies = strategies
        self._fallback = fallback

    def chunk(self, text: str) -> list[Chunk]:
        profile = self._profiler.profile(text)
        return self._strategies.get(profile, self._fallback).chunk(text)
