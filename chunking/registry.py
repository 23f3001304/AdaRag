"""Chunker registry: build the profile -> strategy router, or a plain naive chunker."""

from __future__ import annotations

from chunking.adaptive import AdaptiveChunker
from chunking.base import Chunker
from chunking.code_ast import CodeChunker
from chunking.naive import NaiveChunker
from chunking.notes import NotesChunker
from chunking.paper_section import PaperSectionChunker
from chunking.profile import DocProfile, DocumentProfiler


def build_chunker(chunk_size: int, chunk_overlap: int, adaptive: bool = True) -> Chunker:
    """Return the adaptive profile-routed chunker, or a plain naive chunker when adaptive is off."""
    fallback = NaiveChunker(chunk_size, chunk_overlap)
    if not adaptive:
        return fallback
    strategies: dict[DocProfile, Chunker] = {
        DocProfile.CODE: CodeChunker(),
        DocProfile.PAPER: PaperSectionChunker(),
        DocProfile.NOTES: NotesChunker(),
    }
    return AdaptiveChunker(DocumentProfiler(), strategies, fallback)
