"""Paper-section chunking: split a structured document at headings, keeping sections coherent."""

from __future__ import annotations

import re

from chunking.base import Chunk, Chunker
from chunking.naive import NaiveChunker

_HEADING = re.compile(r"^(#{1,6}\s+\S|\d+(\.\d+)*\.?\s+[A-Z])")


class PaperSectionChunker:
    """One chunk per section (heading + body); over-long sections fall back to size windows."""

    def __init__(self, max_chars: int = 1200, fallback: Chunker | None = None) -> None:
        self._max_chars = max_chars
        self._fallback = fallback or NaiveChunker(max_chars, max_chars // 8)

    def chunk(self, text: str) -> list[Chunk]:
        chunks: list[Chunk] = []
        for body, start in self._sections(text):
            if not body.strip():
                continue
            if len(body) <= self._max_chars:
                chunks.append(Chunk(len(chunks), body.strip(), start, start + len(body)))
                continue
            for sub in self._fallback.chunk(body):
                chunks.append(Chunk(len(chunks), sub.text, start + sub.start, start + sub.end))
        return chunks

    @staticmethod
    def _sections(text: str) -> list[tuple[str, int]]:
        """Group lines into (section_text, start_offset) spans, breaking before each heading."""
        sections: list[tuple[str, int]] = []
        cur: list[str] = []
        cur_start = pos = 0
        for ln in text.splitlines(keepends=True):
            if _HEADING.match(ln) and cur:
                sections.append(("".join(cur), cur_start))
                cur, cur_start = [ln], pos
            else:
                if not cur:
                    cur_start = pos
                cur.append(ln)
            pos += len(ln)
        if cur:
            sections.append(("".join(cur), cur_start))
        return sections
