"""Code chunking by AST: split source at top-level definitions via tree-sitter (DESIGN.md)."""

from __future__ import annotations

from typing import Any

from chunking.base import Chunk, Chunker
from chunking.naive import NaiveChunker

# Top-level definition nodes across common grammars (Python first; degrades for others).
_DEF_TYPES = {
    "function_definition",
    "function_declaration",
    "method_definition",
    "class_definition",
    "class_declaration",
    "decorated_definition",
}


class CodeChunker:
    """Chunks code by top-level AST node: each function/class becomes a chunk, and runs of
    module-level statements (imports, constants) are grouped. Tree-sitter parser, lazy-loaded."""

    def __init__(self, language: str = "python", fallback: Chunker | None = None) -> None:
        self._language = language
        self._parser: Any | None = None
        self._fallback = fallback or NaiveChunker(512, 64)

    def _load(self) -> Any:
        if self._parser is None:
            from tree_sitter import Parser  # deferred: pulls the native parser
            from tree_sitter_language_pack import get_language

            self._parser = Parser(get_language(self._language))
        return self._parser

    def chunk(self, text: str) -> list[Chunk]:
        data = text.encode("utf-8")
        children = self._load().parse(data).root_node.children
        if not any(n.type in _DEF_TYPES for n in children):
            return self._fallback.chunk(text)  # not real code -> naive windows, not one giant chunk
        chunks: list[Chunk] = []
        run: list[tuple[int, int]] = []
        for node in children:
            if node.type in _DEF_TYPES:
                self._flush(chunks, data, run)
                run = []
                self._emit(chunks, data, node.start_byte, node.end_byte)
            else:
                run.append((node.start_byte, node.end_byte))
        self._flush(chunks, data, run)
        return chunks

    def _flush(self, chunks: list[Chunk], data: bytes, run: list[tuple[int, int]]) -> None:
        if run:
            self._emit(chunks, data, run[0][0], run[-1][1])

    @staticmethod
    def _emit(chunks: list[Chunk], data: bytes, start: int, end: int) -> None:
        snippet = data[start:end].decode("utf-8", errors="ignore").strip()
        if snippet:
            chunks.append(Chunk(len(chunks), snippet, start, end))
