"""Chunking contracts: the Chunk value record and the Chunker strategy interface."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class Chunk:
    """A slice of a document: its text and the character span it came from."""

    index: int
    text: str
    start: int
    end: int


@runtime_checkable
class Chunker(Protocol):
    """A chunking strategy. Phase 3 selects the strategy from a file's profile."""

    def chunk(self, text: str) -> list[Chunk]:
        """Split a document's text into chunks."""
        ...
