"""Notes/transcript chunking: smaller, topic-segmented chunks built from blank-line blocks."""

from __future__ import annotations

from chunking.base import Chunk


class NotesChunker:
    """Packs blank-line-delimited blocks (bullets, short paragraphs) into small, topical chunks."""

    def __init__(self, max_chars: int = 320) -> None:
        self._max_chars = max_chars

    def chunk(self, text: str) -> list[Chunk]:
        chunks: list[Chunk] = []
        group: list[str] = []
        g_start = g_end = 0
        for body, start in self._blocks(text):
            if group and len("\n\n".join(group)) + len(body) > self._max_chars:
                chunks.append(Chunk(len(chunks), "\n\n".join(group).strip(), g_start, g_end))
                group = []
            if not group:
                g_start = start
            group.append(body)
            g_end = start + len(body)
        if group:
            chunks.append(Chunk(len(chunks), "\n\n".join(group).strip(), g_start, g_end))
        return chunks

    @staticmethod
    def _blocks(text: str) -> list[tuple[str, int]]:
        """Blank-line-delimited blocks with start offsets (each block is one topical unit)."""
        blocks: list[tuple[str, int]] = []
        cur: list[str] = []
        cur_start = pos = 0
        for ln in text.splitlines(keepends=True):
            if not ln.strip():
                if cur:
                    blocks.append(("".join(cur), cur_start))
                    cur = []
            else:
                if not cur:
                    cur_start = pos
                cur.append(ln)
            pos += len(ln)
        if cur:
            blocks.append(("".join(cur), cur_start))
        return blocks
